package com.example.CodeAssistant;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public record GithubRepositoryDTO(String html_url, String full_name) {}
