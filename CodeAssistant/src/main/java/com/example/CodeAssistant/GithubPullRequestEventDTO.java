package com.example.CodeAssistant;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonIgnoreProperties(ignoreUnknown = true)
public record GithubPullRequestEventDTO(
    String action,
    int number,
    @JsonProperty("pull_request") PullRequest pullRequest,
    GithubRepositoryDTO repository
) {
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record PullRequest(
        String title,
        String state,
        boolean merged,
        Head head
    ) {}

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Head(
        String sha,
        String ref
    ) {}
}
