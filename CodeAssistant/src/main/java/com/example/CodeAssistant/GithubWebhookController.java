package com.example.CodeAssistant;

import com.example.CodeAssistant.service.GithubWebhookService;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/webhook")
public class GithubWebhookController {

    private static final Logger log = LoggerFactory.getLogger(GithubWebhookController.class);

    private final GithubWebhookService webhookService;
    private final ObjectMapper objectMapper;

    public GithubWebhookController(GithubWebhookService webhookService, ObjectMapper objectMapper) {
        this.webhookService = webhookService;
        this.objectMapper = objectMapper;
    }

    /**
     * Unified GitHub webhook endpoint.
     * Routes to the correct handler based on X-GitHub-Event header.
     */
    @PostMapping("/github")
    public ResponseEntity<String> handleGithubWebhook(
            @RequestHeader("X-GitHub-Event") String event,
            @RequestBody String rawPayload) {
        log.info("GitHub webhook alındı — event: {}", event);

        try {
            return switch (event) {
                case "push" -> {
                    GithubPushEventDTO payload = objectMapper.readValue(rawPayload, GithubPushEventDTO.class);
                    webhookService.processPushEvent(payload);
                    yield ResponseEntity.ok("Push event başarıyla işlendi.");
                }
                case "pull_request" -> {
                    GithubPullRequestEventDTO payload = objectMapper.readValue(rawPayload,
                            GithubPullRequestEventDTO.class);
                    webhookService.processPullRequestEvent(payload);
                    yield ResponseEntity.ok("PR event başarıyla işlendi.");
                }
                case "ping" -> {
                    log.info("GitHub ping alındı — webhook bağlantısı başarılı.");
                    yield ResponseEntity.ok("pong");
                }
                default -> {
                    log.info("Desteklenmeyen event tipi: {}", event);
                    yield ResponseEntity.ok("Event tipi yoksayıldı: " + event);
                }
            };
        } catch (Exception e) {
            log.error("Webhook payload parse hatası (event={}): {}", event, e.getMessage(), e);
            return ResponseEntity.badRequest().body("Payload parse edilemedi: " + e.getMessage());
        }
    }

    /**
     * Legacy endpoint — sadece push için. Geriye uyumluluk.
     */
    @PostMapping("/push")
    public ResponseEntity<String> handleGithubPush(@RequestBody GithubPushEventDTO eventPayload) {
        webhookService.processPushEvent(eventPayload);
        return ResponseEntity.ok("Webhook başarıyla alındı ve işlendi.");
    }
}
