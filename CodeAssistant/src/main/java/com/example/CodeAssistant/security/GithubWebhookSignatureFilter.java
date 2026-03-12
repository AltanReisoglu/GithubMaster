package com.example.CodeAssistant.security;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.security.InvalidKeyException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

@Component
public class GithubWebhookSignatureFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(GithubWebhookSignatureFilter.class);

    @Value("${github.webhook.secret}")
    private String secretKey;
    private final String algorithm = "HmacSHA256";

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {

        String path = request.getRequestURI();
        if (!path.startsWith("/api/webhook/")) {
            filterChain.doFilter(request, response);
            return;
        }

        CachedBodyHttpServletRequest wrappedRequest = new CachedBodyHttpServletRequest(request);

        String githubSignature = wrappedRequest.getHeader("X-Hub-Signature-256");

        byte[] byteArray = wrappedRequest.getCachedBody();

        SecretKeySpec secretKeySpec = new SecretKeySpec(this.secretKey.getBytes(),algorithm);

        log.debug("Güvenlik Filtresi Devrede!");
        log.debug("Gelen İmza: {}", githubSignature);

        try
        {
            Mac mac = Mac.getInstance(algorithm);
            mac.init(secretKeySpec);

            byte[] payloadBytes = wrappedRequest.getCachedBody();
            byte[] payloadHashed = mac.doFinal(payloadBytes);

            String calculatedSignature = "sha256=" + bytesToHex(payloadHashed);
            log.debug("Hesaplanan secret: {}", calculatedSignature);

            if (githubSignature != null && MessageDigest.isEqual(calculatedSignature.getBytes(), githubSignature.getBytes())) {
                log.info("Webhook imzası doğrulandı — istek kabul edildi.");

                filterChain.doFilter(wrappedRequest, response);
            } else {
                log.warn("Geçersiz webhook imzası! İstek reddedildi.");

                response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                return;
            }
        }catch (NoSuchAlgorithmException | InvalidKeyException e) {
            log.error("İmza doğrulama hatası: {}", e.getMessage(), e);
            response.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
            return;
        }
    }

    private String bytesToHex(byte[] byteArr)
    {
        StringBuilder hexString = new StringBuilder(byteArr.length * 2);
        for(byte b : byteArr)
        {
            String hex = Integer.toHexString(0xff & b);
            if (hex.length() == 1) {
                hexString.append('0');
            }
            hexString.append(hex);
        }
        return hexString.toString();
    }
}