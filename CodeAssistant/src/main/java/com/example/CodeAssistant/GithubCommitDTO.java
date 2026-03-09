package com.example.CodeAssistant;

import java.util.List;

public record GithubCommitDTO (String name, String email,String id,List<String> added, List<String> modified, List<String> removed) { }
