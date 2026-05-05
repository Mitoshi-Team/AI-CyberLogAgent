/*
 * YARA Rule: Protocol_Anomalies
 */

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
