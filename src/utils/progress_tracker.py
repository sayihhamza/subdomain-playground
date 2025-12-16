"""
Progress tracker for real-time subdomain scan updates
"""
import time
import threading
from typing import Optional, Dict
from datetime import datetime, timedelta


class ProgressTracker:
    """Track and display real-time progress of subdomain scans"""

    def __init__(self, total_domains: int, workers: int):
        """
        Initialize progress tracker

        Args:
            total_domains: Total number of domains to scan
            workers: Number of concurrent workers
        """
        self.total_domains = total_domains
        self.workers = workers
        self.completed = 0
        self.start_time = None
        self.lock = threading.Lock()

    def start(self):
        """Start the progress tracker"""
        self.start_time = time.time()
        self._print_header()

    def _print_header(self):
        """Print initial header with time estimation"""
        # Estimate time (roughly 2-4 minutes per domain with workers)
        avg_time_per_domain = 180  # 3 minutes average
        total_seconds = (self.total_domains / self.workers) * avg_time_per_domain

        estimated_duration = timedelta(seconds=int(total_seconds))
        estimated_completion = datetime.now() + estimated_duration

        print("\n" + "=" * 100)
        print(f"📊 SCAN INITIATED")
        print("=" * 100)
        print(f"Total Domains    : {self.total_domains}")
        print(f"Concurrent Workers: {self.workers}")
        print(f"Estimated Time   : {estimated_duration}")
        print(f"Estimated Done   : {estimated_completion.strftime('%H:%M:%S')}")
        print("=" * 140)
        print(f"{'SUBDOMAIN':<50} {'STATUS':<10} {'PROVIDER':<15} {'CNAME CHAIN':<35} {'DNS INFO':<30}")
        print("=" * 140)

    def update(self, subdomain: str, status: str = "✓", provider: Optional[str] = None,
               cname: Optional[str] = None, http_status: Optional[int] = None,
               fingerprint: Optional[str] = None, vulnerable: bool = False,
               cname_chain: Optional[list] = None, cname_chain_count: int = 0,
               dns_response_code: Optional[str] = None, a_records: Optional[list] = None,
               final_cname_target: Optional[str] = None, http_body_snippet: Optional[str] = None,
               takeover_evidence: Optional[str] = None):
        """
        Update progress with a completed subdomain

        Args:
            subdomain: The subdomain that was processed
            status: Status indicator (✓, ✗, ⚠)
            provider: Cloud provider detected
            cname: CNAME record
            http_status: HTTP status code
            fingerprint: Vulnerability fingerprint
            cname_chain: Full CNAME chain
            cname_chain_count: Number of CNAMEs in chain
            dns_response_code: DNS response code
            a_records: A records
            final_cname_target: Final CNAME destination
        """
        with self.lock:
            self.completed += 1

            # Truncate long values
            subdomain_display = subdomain[:48] + ".." if len(subdomain) > 50 else subdomain
            provider_display = provider or "-"

            # CNAME Chain column - show chain if available
            if cname_chain and len(cname_chain) > 1:
                # Show chain with arrow notation
                chain_str = " → ".join(cname_chain[:2])  # Show first 2 hops
                if len(cname_chain) > 2:
                    chain_str += f" → ...({len(cname_chain)} hops)"
                cname_display = chain_str[:33] + ".." if len(chain_str) > 35 else chain_str
            elif cname:
                cname_display = cname[:33] + ".." if len(cname) > 35 else cname
            else:
                cname_display = "-"

            # Status column shows HTTP status code or vulnerability
            if vulnerable:
                status_display = "🔴 VULN"
            elif http_status:
                status_display = str(http_status)
            else:
                status_display = "-"

            # DNS INFO column - show detailed DNS information
            dns_info_parts = []
            if dns_response_code and dns_response_code != 'NOERROR':
                dns_info_parts.append(f"DNS:{dns_response_code}")
            if a_records:
                dns_info_parts.append(f"A:{len(a_records)}IPs")
            if cname_chain_count > 1:
                dns_info_parts.append(f"Chain:{cname_chain_count}")
            if final_cname_target and final_cname_target != cname:
                dns_info_parts.append(f"→{final_cname_target[:15]}")

            dns_info_display = " | ".join(dns_info_parts) if dns_info_parts else "-"
            dns_info_display = dns_info_display[:28] + ".." if len(dns_info_display) > 30 else dns_info_display

            # Print progress line
            print(f"{subdomain_display:<50} {status_display:<10} {provider_display:<15} {cname_display:<35} {dns_info_display:<30}")

            # Show takeover evidence if present (important!)
            if takeover_evidence:
                print(f"    └─ EVIDENCE: {takeover_evidence}")
            if http_body_snippet and http_body_snippet != "[No error message found]":
                # Truncate snippet for display
                snippet_display = http_body_snippet[:120] + "..." if len(http_body_snippet) > 120 else http_body_snippet
                print(f"    └─ MESSAGE: {snippet_display}")

            # Show progress every 10 domains or at completion
            if self.completed % 10 == 0 or self.completed == self.total_domains:
                self._print_progress()

    def _print_progress(self):
        """Print progress statistics"""
        elapsed = time.time() - self.start_time
        rate = self.completed / elapsed if elapsed > 0 else 0
        remaining = self.total_domains - self.completed
        eta_seconds = remaining / rate if rate > 0 else 0

        progress_pct = (self.completed / self.total_domains) * 100

        print(f"\n[{self.completed}/{self.total_domains}] {progress_pct:.1f}% complete | "
              f"Rate: {rate:.2f} domains/sec | ETA: {int(eta_seconds//60)}m {int(eta_seconds%60)}s\n")

    def finish(self):
        """Print completion summary"""
        elapsed = time.time() - self.start_time
        print("\n" + "=" * 140)
        print(f"✅ SCAN COMPLETE - {self.completed} subdomains processed in {int(elapsed//60)}m {int(elapsed%60)}s")
        print("=" * 140 + "\n")


class SubdomainProgressTracker:
    """Track progress for individual subdomain within a domain scan"""

    def __init__(self, domain: str):
        """
        Initialize subdomain tracker

        Args:
            domain: Domain being scanned
        """
        self.domain = domain
        self.subdomain_results = []
        self.lock = threading.Lock()

    def add_result(self, subdomain: str, provider: Optional[str] = None,
                   cname: Optional[str] = None, http_status: Optional[int] = None,
                   ip_address: Optional[str] = None, vulnerable: bool = False):
        """
        Add a subdomain result

        Args:
            subdomain: Subdomain found
            provider: Cloud provider
            cname: CNAME record
            http_status: HTTP status code
            ip_address: IP address
            vulnerable: Whether vulnerable
        """
        with self.lock:
            self.subdomain_results.append({
                'subdomain': subdomain,
                'provider': provider,
                'cname': cname,
                'http_status': http_status,
                'ip_address': ip_address,
                'vulnerable': vulnerable
            })

    def print_live_result(self, subdomain: str, provider: Optional[str] = None,
                         cname: Optional[str] = None, http_status: Optional[int] = None,
                         vulnerable: bool = False):
        """
        Print a live result as it's discovered

        Args:
            subdomain: Subdomain found
            provider: Cloud provider
            cname: CNAME record
            http_status: HTTP status code
            vulnerable: Whether vulnerable
        """
        status_emoji = "🔴" if vulnerable else ("✓" if http_status and http_status < 400 else "⚠")
        provider_str = f"[{provider}]" if provider else ""
        cname_str = f"→ {cname}" if cname else ""
        http_str = f"HTTP:{http_status}" if http_status else ""
        vuln_str = "⚠️  VULNERABLE" if vulnerable else ""

        print(f"  {status_emoji} {subdomain} {provider_str} {cname_str} {http_str} {vuln_str}")
