package com.example.CodeAssistant;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public record AgentAnalysisResponseDTO(
    String status,
    String message
) {}
