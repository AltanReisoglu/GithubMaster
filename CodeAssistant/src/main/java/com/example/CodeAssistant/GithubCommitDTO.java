package com.example.CodeAssistant;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public record GithubCommitDTO (
    String id,
    String message,
    String timestamp,
    GithubAuthorDTO author,
    List<String> added,
    List<String> modified,
    List<String> removed
) {
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record GithubAuthorDTO(String name, String email, String username) {}
}
