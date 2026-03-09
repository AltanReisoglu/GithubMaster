package com.example.CodeAssistant;

import com.example.CodeAssistant.service.GithubWebhookService;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.Errors;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/webhook")
public class GithubWebhookController {

    private final GithubWebhookService webhookService;

    public GithubWebhookController(GithubWebhookService webhookService)
    {
        this.webhookService = webhookService;
    }

    @PostMapping("/push")
    public ResponseEntity<String> handleGithubPush(@RequestBody GithubPushEventDTO eventPayload) {

        webhookService.processPushEvent(eventPayload);

        return ResponseEntity.ok("Webhook başarıyla alındı ve işlendi.");
    }
}
