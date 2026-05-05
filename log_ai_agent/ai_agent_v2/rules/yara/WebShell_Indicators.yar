/*
 * YARA Rule: WebShell_Indicators
 */

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
