/*
 * YARA Rule: Sensitive_File_Access
 */

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
