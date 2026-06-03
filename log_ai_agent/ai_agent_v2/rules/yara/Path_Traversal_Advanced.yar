/*
 * YARA Rule: Path_Traversal_Advanced
 */

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
