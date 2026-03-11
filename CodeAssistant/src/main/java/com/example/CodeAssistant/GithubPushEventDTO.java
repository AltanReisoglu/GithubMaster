package com.example.CodeAssistant;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public record GithubPushEventDTO(
    String ref,
    String before,
    String after,
    GithubRepositoryDTO repository,
    List<GithubCommitDTO> commits
) {}
