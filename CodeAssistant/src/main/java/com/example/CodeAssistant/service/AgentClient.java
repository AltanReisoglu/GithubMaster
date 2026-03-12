package com.example.CodeAssistant.service;

import com.example.CodeAssistant.AgentAnalysisRequestDTO;
import com.example.CodeAssistant.AgentAnalysisResponseDTO;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;

import java.util.concurrent.CompletableFuture;

@Component
public class AgentClient {

    private static final Logger log = LoggerFactory.getLogger(AgentClient.class);

    private final RestTemplate restTemplate;
    private final String agentBaseUrl;

    private static final int MAX_RETRIES = 3;
    private static final long RETRY_DELAY_MS = 2000;

    public AgentClient(
            @Value("${agent.api.base-url}") String agentBaseUrl,
            @Value("${agent.api.connect-timeout-ms}") int connectTimeout,
            @Value("${agent.api.read-timeout-ms}") int readTimeout
    ) {
        this.agentBaseUrl = agentBaseUrl;

        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(connectTimeout);
        factory.setReadTimeout(readTimeout);
        this.restTemplate = new RestTemplate(factory);
    }

    public void triggerAnalysis(AgentAnalysisRequestDTO request) {
        String url = agentBaseUrl + "/api/agent/review";

        CompletableFuture.runAsync(() -> {
            for (int attempt = 1; attempt <= MAX_RETRIES; attempt++) {
                try {
                    log.info("Agent API'ye istek gönderiliyor (deneme {}/{}): {}", attempt, MAX_RETRIES, url);

                    ResponseEntity<AgentAnalysisResponseDTO> response =
                            restTemplate.postForEntity(url, request, AgentAnalysisResponseDTO.class);

                    AgentAnalysisResponseDTO body = response.getBody();
                    log.info("Agent API yanıtı: {} — status={}, message={}",
                            response.getStatusCode(),
                            body != null ? body.status() : "null",
                            body != null ? body.message() : "null");
                    return; // Başarılı, döngüden çık

                } catch (ResourceAccessException e) {
                    log.warn("Agent API'ye bağlanılamadı (deneme {}/{}): {}", attempt, MAX_RETRIES, e.getMessage());
                    if (attempt < MAX_RETRIES) {
                        try {
                            Thread.sleep(RETRY_DELAY_MS);
                        } catch (InterruptedException ie) {
                            Thread.currentThread().interrupt();
                            log.error("Retry beklemesi kesildi.");
                            return;
                        }
                    }
                } catch (Exception e) {
                    log.error("Agent API çağrısında beklenmeyen hata: {}", e.getMessage(), e);
                    return; // Retry yapılmayan hata
                }
            }
            log.error("Agent API'ye {} deneme sonrası ulaşılamadı. İstek iptal edildi.", MAX_RETRIES);
        }).exceptionally(ex -> {
            log.error("Agent analiz görevi başarısız: {}", ex.getMessage(), ex);
            return null;
        });
    }

    /**
     * Agent API'nin ayakta olup olmadığını kontrol eder.
     */
    public boolean isAgentHealthy() {
        try {
            ResponseEntity<String> response = restTemplate.getForEntity(agentBaseUrl + "/health", String.class);
            return response.getStatusCode().is2xxSuccessful();
        } catch (Exception e) {
            log.warn("Agent health check başarısız: {}", e.getMessage());
            return false;
        }
    }
}
