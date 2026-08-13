---
name: op-recommend
description: "Pentest agent op-recommend. Use for authorized penetration testing tasks."
model: deepseek/deepseek-v4-flash
mode: subagent
---
---|
---|---|---|---|
| "Audit my code for vulnerabilities" | security-auditor | — | Fully implemented |
| "Pentest target.com" | pentester-orchestrator | recon-agent | Full engagement |
| "Scan for open ports" | recon-agent | pentester-executor | Use nmap/masscan |
| "Find subdomains" | recon-agent | — | subfinder/amass/assetfinder |
| "Enumerate directories" | recon-agent | — | ffuf/gobuster/feroxbuster |
| "Crawl the website" | recon-agent | — | katana/gau/waybackurls |
| "Take screenshots" | recon-agent | — | gowitness |
| "Test for SQL injection" | injection-tester | pentester-executor | Fully implemented |
| "Test for XSS" | xss-tester | pentester-executor | Fully implemented |
| "Test for CSRF" | csrf-tester | pentester-executor | Fully implemented |
| "Research CVEs" | cve-tester | — | Fully implemented |
| "Check AD security" | network-pentest-agent | — | BloodHound + kerbrute + impacket |
| "Enumerate SMB/LDAP/SNMP" | network-pentest-agent | — | enum4linux, ldapsearch, snmpwalk |
| "Pivot through network" | post-exploitation-agent | — | chisel, ligolo-ng |
| "Escalate privileges" | post-exploitation-agent | — | linpeas, winpeas, kernel exploits |
| "Crack passwords" | password-attack-agent | — | hashcat, john |
| "Brute-force login" | password-attack-agent | — | hydra, medusa |
| "Spray credentials" | password-attack-agent | — | crackmapexec, kerbrute |
| "Review cloud config" | cloud-security-agent | — | ScoutSuite, cloudfox |
| "Scan containers" | cloud-security-agent | — | trivy, grype |
| "Audit K8s" | cloud-security-agent | — | kubectl auth can-i |
| "Generate pentest report" | pentester-orchestrator | — | Uses handoff.sh for report generation |
| "Chain findings into attack" | pentester-orchestrator | — | Uses chains.sh for attack chain tracking |
| "Test for SSRF" | pentester-executor | — | Map to pentester-executor Phase 3 |
| "Test API security" | pentester-executor | — | Map to pentester-executor |
| "Write Sigma rules" | — | — | Not yet implemented |
| "Plan engagement" | pentester-orchestrator | — | Fully implemented |

## Output Format

When routing a task, produce:

```
**Primary agent**: <name>
**Supporting**: <name or "none">

**Assumed scope**: <one sentence>

**Next commands**:
1. <command>
2. <command>
3. <command>

**Watch for**: <one sentence pitfall>
```
