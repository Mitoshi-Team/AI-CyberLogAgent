/*
 * YARA Rules for Cyber Log Analysis - Core Web Vulnerabilities
 */

rule SQL_Injection_Advanced
{
    meta:
        description = "Detects advanced SQL injection attempts"
        author = "AI CyberLog Agent"
        severity = "high"
        category = "initial_access"
        mitre_ref = "T1190"

    strings:
        // Basic keywords
        $s1 = "UNION" nocase fullword
        $s2 = "SELECT" nocase fullword
        $s3 = "INSERT" nocase fullword
        $s4 = "UPDATE" nocase fullword
        $s5 = "DELETE" nocase fullword
        $s6 = "DROP" nocase fullword
        
        // Logical markers
        $l1 = "OR 1=1" nocase
        $l2 = "' OR '" nocase
        $l3 = "\" OR \"" nocase
        $l4 = "benchmark(" nocase
        $l5 = "sleep(" nocase
        $l6 = "pg_sleep(" nocase
        
        // URL Encoded variants
        $e1 = "UNION%20SELECT" nocase
        $e2 = "UNION+SELECT" nocase
        $e3 = "OR+1%3D1" nocase
        $e4 = "%27+OR+%27" nocase

    condition:
        ($s1 and $s2) or any of ($l*) or any of ($e*) or 2 of ($s*)
}

rule XSS_Advanced
{
    meta:
        description = "Detects cross-site scripting (XSS) attempts"
        author = "AI CyberLog Agent"
        severity = "medium"
        category = "initial_access"
        mitre_ref = "T1190"

    strings:
        // Dangerous tags
        $t1 = "<script" nocase
        $t7 = "<iframe" nocase
        
        // Event handlers
        $t2 = "javascript:" nocase
        $t3 = "onload=" nocase
        $t4 = "onerror=" nocase
        $t5 = "onclick=" nocase
        
        // Dangerous functions
        $t8 = "alert(" nocase
        $t9 = "prompt(" nocase
        $t10 = "confirm(" nocase

        // Encoded
        $e1 = "%3cscript" nocase
        $e2 = "javascript%3a" nocase
        $e3 = "onerror%3d" nocase
        $e4 = "alert%28" nocase

    condition:
        any of ($t1, $t2, $t3, $t4, $t5, $t7, $t8, $t9, $t10, $e*)
}

rule Path_Traversal_Advanced
{
    meta:
        description = "Detects directory traversal and file inclusion"
        author = "AI CyberLog Agent"
        severity = "high"
        category = "discovery"
        mitre_ref = "T1083"

    strings:
        // Unix patterns
        $p1 = "../../"
        $p2 = "/etc/passwd" nocase
        $p3 = "/etc/shadow" nocase
        $p4 = "/etc/group" nocase
        $p5 = "/etc/issue" nocase
        
        // Windows patterns
        $w1 = "..\\..\\"
        $w2 = "C:\\Windows\\System32" nocase
        $w3 = "windows/win.ini" nocase
        $w4 = "boot.ini" nocase
        
        // Encoded
        $e1 = "%2e%2e%2f" nocase
        $e2 = "..%2f" nocase
        $e3 = "%2e%2e/" nocase
        $e4 = "..%5c" nocase

    condition:
        any of them
}

rule Sensitive_File_Access
{
    meta:
        description = "Detects access to sensitive configuration files"
        author = "AI CyberLog Agent"
        severity = "medium"
        category = "discovery"
        mitre_ref = "T1595"

    strings:
        $f1 = "/.env" nocase
        $f2 = "/.git/" nocase
        $f3 = "/.svn/" nocase
        $f4 = "/.htaccess" nocase
        $f5 = "/web.config" nocase
        $f6 = "/config.php" nocase
        $f7 = "/wp-config.php" nocase
        $f8 = "/settings.py" nocase
        $f9 = "/.bash_history" nocase
        $f10 = "/.ssh/" nocase

    condition:
        any of them
}
