/*
 * YARA Rule: SQL_Injection_Advanced
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
