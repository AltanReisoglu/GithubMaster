package com.example.CodeAssistant;

import java.util.List;

public record AgentAnalysisRequestDTO(
    String repository,
    Integer prNumber,
    String commitId,
    List<String> filesToAnalyze,
    String eventType
) {}
