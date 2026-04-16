/*
 * YARA Rules for Cyber Log Analysis
 * 
 * These rules detect common attack patterns in Apache logs.
 * Uses simple, YARA-compatible regex patterns.
 */

rule SQL_Injection_Pattern
{
    meta:
        description = "Detects SQL injection attempts"
        author = "AI CyberLog Agent"
        severity = "high"
        category = "initial_access"
        mitre_ref = "T1190"

    strings:
        $sqli1 = "UNION SELECT" nocase
        $sqli2 = "OR 1=1" nocase
        $sqli3 = "DROP TABLE" nocase
        $sqli4 = "' OR '" nocase
        $sqli5 = "xp_cmdshell" nocase
        $sqli6 = "WAITFOR DELAY" nocase

    condition:
        1 of them
}


rule XSS_Attempt
{
    meta:
        description = "Detects Cross-Site Scripting attempts"
        author = "AI CyberLog Agent"
        severity = "medium"
        category = "initial_access"
        mitre_ref = "T1183"

    strings:
        $xss1 = "<script" nocase
        $xss2 = "javascript:" nocase
        $xss3 = "onerror=" nocase
        $xss4 = "onload=" nocase
        $xss5 = "alert(" nocase

    condition:
        1 of them
}


rule Brute_Force_Indicators
{
    meta:
        description = "Detects brute force authentication attempts"
        author = "AI CyberLog Agent"
        severity = "high"
        category = "credential_access"
        mitre_ref = "T1110"

    strings:
        $bf1 = "Authentication failed" nocase
        $bf2 = "failed login" nocase
        $bf3 = "account locked" nocase
        $bf4 = "brute force" nocase
        $bf5 = "maximum number of tries" nocase
        $bf6 = "Multiple failed login" nocase

    condition:
        1 of them
}


rule Path_Traversal_Attempt
{
    meta:
        description = "Detects path traversal attempts"
        author = "AI CyberLog Agent"
        severity = "high"
        category = "collection"
        mitre_ref = "T1005"

    strings:
        $pt1 = "../" 
        $pt2 = "..\\"
        $pt3 = "script not found" nocase
        $pt4 = "etc/passwd" nocase
        $pt5 = "etc/shadow" nocase

    condition:
        1 of them
}


rule Security_Violation
{
    meta:
        description = "Detects security violations"
        author = "AI CyberLog Agent"
        severity = "medium"
        category = "defense_evasion"
        mitre_ref = "T1070"

    strings:
        $sv1 = "security violation" nocase
        $sv2 = "unauthorized access" nocase
        $sv3 = "access forbidden" nocase
        $sv4 = "permission denied" nocase

    condition:
        1 of them
}


rule Suspicious_Request
{
    meta:
        description = "Detects suspicious URI patterns"
        author = "AI CyberLog Agent"
        severity = "medium"
        category = "discovery"
        mitre_ref = "T1046"

    strings:
        $sr1 = "/admin/" 
        $sr2 = "/wp-admin/" 
        $sr3 = "/wp-login" 
        $sr4 = "/phpmyadmin/" 
        $sr5 = "/.env" 
        $sr6 = "/config/" 
        $sr7 = "/api/" 

    condition:
        1 of them
}
