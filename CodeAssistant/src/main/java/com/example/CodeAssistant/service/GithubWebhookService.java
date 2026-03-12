package com.example.CodeAssistant.service;

import com.example.CodeAssistant.AgentAnalysisRequestDTO;
import com.example.CodeAssistant.GithubCommitDTO;
import com.example.CodeAssistant.GithubPullRequestEventDTO;
import com.example.CodeAssistant.GithubPushEventDTO;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.Arrays;
import java.util.List;
import java.util.stream.Stream;

@Service
public class GithubWebhookService {

    private static final Logger log = LoggerFactory.getLogger(GithubWebhookService.class);

    private final AgentClient agentClient;

    public GithubWebhookService(AgentClient agentClient) {
        this.agentClient = agentClient;
    }

    public static final List<String> SUPPORTED_EXTENSIONS = Arrays.asList(".java", ".c", ".cpp", ".py", ".cs");

    // ─── Push Event ────────────────────────────────────────────

    public void processPushEvent(GithubPushEventDTO event) {
        List<GithubCommitDTO> commits = event.commits();
        if (commits == null || commits.isEmpty()) {
            log.info("Push event'te commit bulunamadı. İşlem atlanıyor.");
            return;
        }

        List<String> filesToAnalyze = commits.stream()
                .flatMap(commit -> Stream.concat(
                        commit.added() != null ? commit.added().stream() : Stream.empty(),
                        commit.modified() != null ? commit.modified().stream() : Stream.empty()
                ))
                .filter(fileName -> SUPPORTED_EXTENSIONS.stream().anyMatch(fileName::endsWith))
                .distinct()
                .toList();

        if (filesToAnalyze.isEmpty()) {
            log.info("İncelenecek desteklenen kod dosyası bulunamadı. İşlem iptal.");
            return;
        }

        log.info("AI analizi için {} dosya tespit edildi: {}", filesToAnalyze.size(), filesToAnalyze);

        String repoFullName = resolveRepoFullName(event.repository().full_name(), event.repository().html_url());
        String commitId = resolveCommitId(event.after(), commits);

        AgentAnalysisRequestDTO request = new AgentAnalysisRequestDTO(
                repoFullName,
                null,
                commitId,
                filesToAnalyze,
                "push"
        );

        log.info("Agent analiz isteği tetikleniyor: repo={}, commit={}", repoFullName, commitId);
        agentClient.triggerAnalysis(request);
    }

    // ─── Pull Request Event ────────────────────────────────────

    public void processPullRequestEvent(GithubPullRequestEventDTO event) {
        String action = event.action();

        // Sadece opened ve synchronize (yeni commit push'landığında) action'larını işle
        if (!"opened".equals(action) && !"synchronize".equals(action)) {
            log.info("PR action '{}' yoksayıldı (sadece opened/synchronize desteklenir).", action);
            return;
        }

        int prNumber = event.number();
        String repoFullName = resolveRepoFullName(
                event.repository().full_name(),
                event.repository().html_url()
        );

        if (repoFullName == null) {
            log.error("PR event'ten repo adı çözümlenemedi. İşlem iptal.");
            return;
        }

        String headSha = null;
        if (event.pullRequest() != null && event.pullRequest().head() != null) {
            headSha = event.pullRequest().head().sha();
        }

        log.info("PR #{} ({}) analizi başlatılıyor — repo={}, head={}",
                prNumber, action, repoFullName, headSha);

        // PR event'ler için filesToAnalyze boş gönderiyoruz;
        // Python tarafı PR numarasından diff çekip dosyaları kendisi belirleyecek.
        AgentAnalysisRequestDTO request = new AgentAnalysisRequestDTO(
                repoFullName,
                prNumber,
                headSha,
                List.of(),  // Python tarafı PR diff'ten dosya listesini çıkaracak
                "pull_request"
        );

        agentClient.triggerAnalysis(request);
    }

    // ─── Yardımcı Metodlar ─────────────────────────────────────

    private String resolveRepoFullName(String fullName, String htmlUrl) {
        if (fullName != null && !fullName.isBlank()) {
            return fullName;
        }
        if (htmlUrl != null) {
            return htmlUrl.replace("https://github.com/", "");
        }
        return null;
    }

    private String resolveCommitId(String after, List<GithubCommitDTO> commits) {
        if (after != null && !after.isBlank()) {
            return after;
        }
        if (commits != null && !commits.isEmpty()) {
            return commits.get(commits.size() - 1).id();
        }
        return null;
    }
}
