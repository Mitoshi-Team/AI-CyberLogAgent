/*
 * YARA Rules for Cyber Log Analysis - RCE and Web Shells
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

rule WebShell_Indicators
{
    meta:
        description = "Detects presence or usage of web shells"
        author = "AI CyberLog Agent"
        severity = "critical"
        category = "persistence"
        mitre_ref = "T1505.003"

    strings:
        // Common web shell filenames
        $f1 = "c99.php" nocase
        $f2 = "r57.php" nocase
        $f3 = "shell.php" nocase
        $f4 = "b374k.php" nocase
        $f5 = "wso.php" nocase
        $f6 = "cmd.jsp" nocase
        $f7 = "cmd.asp" nocase
        $f8 = "cmd.aspx" nocase
        
        // Execution parameters
        $p1 = "?cmd=" nocase
        $p2 = "&cmd=" nocase
        $p3 = "?exec=" nocase
        $p4 = "&exec=" nocase
        $p5 = "?command=" nocase
        $p6 = "system(" nocase
        $p7 = "passthru(" nocase
        $p8 = "eval(base64_decode" nocase

    condition:
        any of them
}
