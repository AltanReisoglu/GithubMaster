package com.example.CodeAssistant;

import java.util.List;

public record GithubPushEventDTO(GithubRepositoryDTO repository, List<GithubCommitDTO> commits) { }
