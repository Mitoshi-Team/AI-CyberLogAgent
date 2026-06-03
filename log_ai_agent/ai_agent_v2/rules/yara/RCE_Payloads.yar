/*
 * YARA Rule: RCE_Payloads
 */

rule RCE_Payloads
{
    meta:
        description = "Detects common RCE payloads and command execution"
        author = "AI CyberLog Agent"
        severity = "critical"
        category = "execution"
        mitre_ref = "T1059"

    strings:
        // Linux commands
        $c1 = "bin/sh" nocase
        $c2 = "bin/bash" nocase
        $c3 = "curl " nocase
        $c4 = "wget " nocase
        $c5 = "python -c" nocase
        $c6 = "perl -e" nocase
        $c7 = "id;whoami" nocase
        $c8 = "uname -a" nocase
        
        // Windows commands
        $w1 = "cmd.exe" nocase
        $w2 = "powershell" nocase
        $w3 = "certutil" nocase
        $w4 = "bitsadmin" nocase
        
        // General shell patterns
        $g1 = "reverse_shell" nocase
        $g2 = "/dev/tcp/" nocase
        $g3 = "tcpconn" nocase
        
        // Log4Shell
        $l1 = "${jndi:ldap:" nocase
        $l2 = "${jndi:rmi:" nocase
        $l3 = "${jndi:dns:" nocase

    condition:
        any of them
}
