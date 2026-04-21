/*
 * YARA Rules for Cyber Log Analysis - Scanners and Anomalies
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

rule Protocol_Anomalies
{
    meta:
        description = "Detects HTTP protocol anomalies"
        author = "AI CyberLog Agent"
        severity = "low"
        category = "discovery"
        mitre_ref = "T1046"

    strings:
        // Dangerous methods if found in logs (though parsers usually extract method separately)
        // This engine joins fields, so we might see them
        $m1 = "PUT /" 
        $m2 = "DELETE /" 
        $m3 = "TRACE /" 
        $m4 = "CONNECT /"
        
        // Suspicious version strings or headers
        $h1 = "HTTP/1.0" fullword
        $h2 = "User-Agent: -" fullword
        $h3 = "Referer: -" fullword

    condition:
        any of them
}
