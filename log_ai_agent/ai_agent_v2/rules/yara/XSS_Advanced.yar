/*
 * YARA Rule: XSS_Advanced
 */

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
