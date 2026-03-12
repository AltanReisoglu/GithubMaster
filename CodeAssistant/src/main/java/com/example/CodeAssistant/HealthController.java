package com.example.CodeAssistant;

import com.example.CodeAssistant.service.AgentClient;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api")
public class HealthController {

    private final AgentClient agentClient;

    public HealthController(AgentClient agentClient) {
        this.agentClient = agentClient;
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> health() {
        boolean agentUp = agentClient.isAgentHealthy();

        Map<String, Object> status = Map.of(
                "status", agentUp ? "healthy" : "degraded",
                "java_backend", "up",
                "python_agent", agentUp ? "up" : "down"
        );

        return agentUp
                ? ResponseEntity.ok(status)
                : ResponseEntity.status(503).body(status);
    }
}
