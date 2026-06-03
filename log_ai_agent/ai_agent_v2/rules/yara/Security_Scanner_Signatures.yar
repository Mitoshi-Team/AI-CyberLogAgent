/*
 * YARA Rule: Security_Scanner_Signatures
 */

rule Security_Scanner_Signatures
{
    meta:
        description = "Detects advanced signatures of security scanners"
        author = "AI CyberLog Agent"
        severity = "medium"
        category = "discovery"
        mitre_ref = "T1595"

    strings:
        // Headers/Agents (beyond Sigma)
        $a1 = "Acunetix" nocase
        $a2 = "Netsparker" nocase
        $a3 = "AppScan" nocase
        $a4 = "OpenVAS" nocase
        $a5 = "Nessus" nocase
        $a6 = "Qualys" nocase
        $a7 = "Nikto" nocase
        $a8 = "sqlmap" nocase
        
        // Scanner specific URI patterns
        $u1 = "nessustest" nocase
        $u2 = "appscan_fingerprint" nocase
        $u3 = "w00tw00t" nocase
        $u4 = "Nmap Scripting Engine" nocase
        $u5 = "muieblackcat" nocase

    condition:
        any of them
}
