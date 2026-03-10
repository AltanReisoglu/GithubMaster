package com.example.CodeAssistant.service;

import com.example.CodeAssistant.AgentAnalysisRequestDTO;
import com.example.CodeAssistant.GithubCommitDTO;
import com.example.CodeAssistant.GithubPushEventDTO;
import org.springframework.stereotype.Service;

import java.util.Arrays;
import java.util.List;
import java.util.stream.Stream;

@Service
public class GithubWebhookService {

    private final AgentClient agentClient;

    public GithubWebhookService(AgentClient agentClient) {
        this.agentClient = agentClient;
    }

    public static List<String> fileTypes = Arrays.asList(new String[] {".java" , ".c" , ".cpp" , ".py" });

    public void processPushEvent(GithubPushEventDTO event)
    {
        List<GithubCommitDTO> commits = event.commits();

        List<String> filesToAnalyze = commits.stream()
                .flatMap(commit -> Stream.concat(commit.added().stream(), commit.modified().stream()))
                .filter(fileName -> fileTypes.stream().anyMatch(ext -> fileName.endsWith(ext))).toList();

        if (filesToAnalyze.isEmpty()) {
            System.out.println("İncelenecek kod dosyası bulunamadı. İşlem iptal!");
            return;
        }

        System.out.println("AI'a gönderilecek kod dosyaları bulundu:");
        filesToAnalyze.forEach(System.out::println);

        String repoFullName = event.repository().full_name();
        if (repoFullName == null && event.repository().html_url() != null) {
            repoFullName = event.repository().html_url().replace("https://github.com/", "");
        }

        String commitId = null;
        if (commits != null && !commits.isEmpty()) {
            commitId = commits.get(commits.size() - 1).id();
        }

        AgentAnalysisRequestDTO request = new AgentAnalysisRequestDTO(
                repoFullName,
                null,
                commitId,
                filesToAnalyze,
                "push"
        );
        
        System.out.println("Tetiklenen Agent Analiz İsteği: " + request);
        agentClient.triggerAnalysis(request);
    }

}
