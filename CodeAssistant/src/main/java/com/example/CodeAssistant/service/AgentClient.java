package com.example.CodeAssistant.service;

import com.example.CodeAssistant.AgentAnalysisRequestDTO;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

@Component
public class AgentClient {

    private final RestTemplate restTemplate;
    
    private final String agentBaseUrl = "http://localhost:8000";

    public AgentClient() {
        this.restTemplate = new RestTemplate();
    }

    public void triggerAnalysis(AgentAnalysisRequestDTO request) {
        String url = agentBaseUrl + "/api/agent/review";
        try {
            System.out.println("Sending async request to Agent API at: " + url);
            ResponseEntity<String> response = restTemplate.postForEntity(url, request, String.class);
            System.out.println("Agent API response: " + response.getStatusCode() + " - " + response.getBody());
        } catch (Exception e) {
            System.err.println("Error calling Agent API: " + e.getMessage());
        }
    }
}
