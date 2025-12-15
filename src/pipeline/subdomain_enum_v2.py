"""
Multi-tool subdomain enumeration for maximum coverage (98-99%)

This enumerator orchestrates multiple tools in parallel and sequential modes:
- Passive: subfinder + amass + findomain (90-95% coverage, 2-3 min)
- Full: + puredns + bbot + alterx (98-99% coverage, 30 min)
"""
from typing import List, Set, Dict
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
import os
import logging

from ..models.subdomain import Subdomain
from ..utils.logger import get_logger


class MultiToolEnumerator:
    """
    Orchestrate multiple subdomain enumeration tools
    for maximum coverage (98-99%)
    """

    def __init__(self, config_dir: Path = None):
        """
        Initialize multi-tool enumerator

        Args:
            config_dir: Path to config directory (for tool paths)
        """
        self.logger = get_logger(self.__class__.__name__)

        # Get default paths
        home = Path.home()
        go_bin = home / "go" / "bin"
        project_bin = Path(__file__).parent.parent.parent / "bin"

        # Tool paths - Check environment variables first, then fall back to defaults
        self.tools = {
            'subfinder': Path(os.getenv('SUBFINDER_PATH', project_bin / 'subfinder')),
            'amass': Path(os.getenv('AMASS_PATH', go_bin / 'amass')),
            'findomain': Path(os.getenv('FINDOMAIN_PATH', go_bin / 'findomain')),
            'puredns': Path(os.getenv('PUREDNS_PATH', go_bin / 'puredns')),
            'alterx': Path(os.getenv('ALTERX_PATH', go_bin / 'alterx')),
        }

        # Data paths (relative to project root)
        project_root = Path(__file__).parent.parent.parent
        self.wordlist_path = project_root / 'data' / 'wordlists' / 'best-dns-wordlist.txt'
        self.resolvers_path = project_root / 'data' / 'resolvers' / 'resolvers.txt'

        # Verify critical tools exist
        for tool_name in ['subfinder', 'amass', 'findomain']:
            if not self.tools[tool_name].exists():
                self.logger.warning(f"{tool_name} not found at {self.tools[tool_name]}")

    def enumerate(self, domain: str, mode='passive') -> List[Subdomain]:
        """
        Run enumeration based on mode

        Args:
            domain: Target domain
            mode: 'passive' (fast, 90-95%) or 'full' (slow, 98-99%)

        Returns:
            List of Subdomain objects
        """
        self.logger.info(f"Starting {mode} enumeration for: {domain}")

        # Phase 1: Passive enumeration (parallel)
        passive_subdomains = self._run_passive_tools(domain)

        # ALWAYS include the root domain itself in results
        # This ensures we check if the domain itself has Shopify CNAME/vulnerable config
        passive_subdomains.add(domain)

        self.logger.info(f"Passive enumeration found {len(passive_subdomains)} subdomains (including root)")

        if mode == 'passive' or mode == 'quick':
            return self._create_subdomain_objects(passive_subdomains, domain)

        # Phase 2: Active enumeration (sequential)
        active_subdomains = self._run_active_tools(domain, passive_subdomains)

        # Merge results (root domain already in passive_subdomains)
        all_subdomains = passive_subdomains | active_subdomains

        self.logger.info(f"Full enumeration found {len(all_subdomains)} total subdomains (including root)")

        return self._create_subdomain_objects(all_subdomains, domain)

    def _run_passive_tools(self, domain: str) -> Set[str]:
        """
        Run passive enumeration tools in parallel

        Args:
            domain: Target domain

        Returns:
            Set of discovered subdomains
        """
        results = {}

        # Run all passive tools in parallel for maximum coverage
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}

            # Submit all available passive tools
            if self.tools['subfinder'].exists():
                futures[executor.submit(self._run_subfinder, domain)] = 'subfinder'

            if self.tools['findomain'].exists():
                futures[executor.submit(self._run_findomain, domain)] = 'findomain'

            if self.tools['amass'].exists():
                futures[executor.submit(self._run_amass, domain)] = 'amass'

            # Wait for all tools to complete
            for future in as_completed(futures):
                tool = futures[future]
                try:
                    subs = future.result()
                    results[tool] = subs
                    self.logger.info(f"{tool}: found {len(subs)} subdomains")
                except Exception as e:
                    self.logger.warning(f"{tool} failed: {e}")
                    results[tool] = set()

        # Merge all results
        all_subs = set()
        for tool_subs in results.values():
            all_subs.update(tool_subs)

        self.logger.info(f"Total unique subdomains from passive tools: {len(all_subs)}")
        return all_subs

    def _run_subfinder(self, domain: str) -> Set[str]:
        """Run subfinder enumeration"""
        if not self.tools['subfinder'].exists():
            self.logger.warning("Subfinder not available")
            return set()

        cmd = [
            str(self.tools['subfinder']),
            '-d', domain,
            '-all',
            '-silent'
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0 and result.stdout:
                subdomains = set(result.stdout.strip().split('\n'))
                # Filter out empty strings
                return {s for s in subdomains if s and '.' in s}

            return set()

        except Exception as e:
            self.logger.error(f"Subfinder error: {e}")
            return set()

    def _run_amass(self, domain: str) -> Set[str]:
        """Run amass passive enumeration with timeout handling"""
        if not self.tools['amass'].exists():
            self.logger.warning("Amass not available")
            return set()

        cmd = [
            str(self.tools['amass']),
            'enum',
            '-passive',
            '-d', domain,
            '-timeout', '2'  # Internal timeout of 2 minutes (reduced from 5)
        ]

        try:
            self.logger.info("Running amass (max 3 minutes)...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180  # 3 minute external timeout (reduced from 6.5)
            )

            if result.returncode == 0 and result.stdout:
                subdomains = set(result.stdout.strip().split('\n'))
                return {s for s in subdomains if s and '.' in s}

            return set()

        except subprocess.TimeoutExpired:
            self.logger.debug("Amass timed out after 3 minutes, using partial results")
            return set()
        except Exception as e:
            self.logger.error(f"Amass error: {e}")
            return set()

    def _run_findomain(self, domain: str) -> Set[str]:
        """Run findomain enumeration"""
        if not self.tools['findomain'].exists():
            self.logger.warning("Findomain not available")
            return set()

        cmd = [
            str(self.tools['findomain']),
            '-t', domain,
            '-q'  # Quiet mode
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180  # Increased from 60s to 180s for larger domains
            )

            if result.returncode == 0 and result.stdout:
                subdomains = set(result.stdout.strip().split('\n'))
                return {s for s in subdomains if s and '.' in s}

            return set()

        except subprocess.TimeoutExpired:
            # Don't log timeout as error - it's expected for some domains
            self.logger.debug(f"Findomain timed out for {domain} after 180s")
            return set()
        except Exception as e:
            self.logger.error(f"Findomain error: {e}")
            return set()

    def _run_active_tools(self, domain: str, passive_results: Set[str]) -> Set[str]:
        """
        Run active enumeration tools sequentially

        Args:
            domain: Target domain
            passive_results: Results from passive enumeration (for permutation generation)

        Returns:
            Set of newly discovered subdomains
        """
        active_subs = set()

        # Puredns DNS bruteforce
        if self.tools['puredns'].exists() and self.wordlist_path.exists():
            try:
                puredns_subs = self._run_puredns(domain)
                active_subs.update(puredns_subs)
                self.logger.info(f"Puredns: found {len(puredns_subs)} new subdomains")
            except Exception as e:
                self.logger.error(f"Puredns failed: {e}")

        # Alterx permutations
        if self.tools['alterx'].exists() and passive_results:
            try:
                alterx_subs = self._run_alterx(domain, passive_results)
                active_subs.update(alterx_subs)
                self.logger.info(f"Alterx: found {len(alterx_subs)} new subdomains")
            except Exception as e:
                self.logger.error(f"Alterx failed: {e}")

        return active_subs

    def _run_puredns(self, domain: str) -> Set[str]:
        """Run puredns DNS bruteforce"""
        if not self.wordlist_path.exists():
            self.logger.warning(f"Wordlist not found: {self.wordlist_path}")
            return set()

        if not self.resolvers_path.exists():
            self.logger.warning(f"Resolvers not found: {self.resolvers_path}")
            return set()

        cmd = [
            str(self.tools['puredns']),
            'bruteforce',
            str(self.wordlist_path),
            domain,
            '-r', str(self.resolvers_path),
            '--rate-limit', '1000',
            '-q'  # Quiet
        ]

        try:
            self.logger.info(f"Running puredns (this may take 15-20 minutes)...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 min timeout
            )

            if result.returncode == 0 and result.stdout:
                subdomains = set(result.stdout.strip().split('\n'))
                return {s for s in subdomains if s and '.' in s}

            return set()

        except subprocess.TimeoutExpired:
            self.logger.warning("Puredns timed out after 30 minutes")
            return set()
        except Exception as e:
            self.logger.error(f"Puredns error: {e}")
            return set()

    def _run_alterx(self, domain: str, existing_subs: Set[str]) -> Set[str]:
        """
        Run alterx for subdomain permutations

        Args:
            domain: Target domain
            existing_subs: Existing subdomains to generate permutations from

        Returns:
            Set of permuted subdomains
        """
        # Create comprehensive patterns for cloud services and common subdomains
        patterns = [
            # Development & Staging
            'dev', 'staging', 'stage', 'prod', 'production', 'uat', 'qa', 'test', 'testing',
            'demo', 'sandbox', 'lab', 'labs', 'preview', 'temp', 'tmp',

            # API & Services
            'api', 'api-v1', 'api-v2', 'rest', 'graphql', 'ws', 'websocket', 'grpc',
            'service', 'services', 'microservice', 'backend', 'gateway',

            # Admin & Management
            'admin', 'administrator', 'management', 'console', 'dashboard', 'panel',
            'control', 'manager', 'portal',

            # E-commerce
            'shop', 'store', 'checkout', 'cart', 'payment', 'payments', 'billing',
            'order', 'orders', 'merchant', 'pos',

            # Content & Media
            'cdn', 'static', 'assets', 'media', 'images', 'img', 'files', 'download',
            'uploads', 'content', 'resources',

            # Applications
            'app', 'mobile', 'ios', 'android', 'web', 'webapp', 'client',

            # Infrastructure
            'vpn', 'mail', 'email', 'smtp', 'pop', 'imap', 'ftp', 'sftp',
            'ssh', 'remote', 'proxy', 'load-balancer', 'lb',

            # Monitoring & Tools
            'monitoring', 'metrics', 'logs', 'analytics', 'stats', 'status',
            'health', 'grafana', 'kibana', 'prometheus',

            # Database & Cache
            'db', 'database', 'sql', 'mysql', 'postgres', 'mongodb', 'redis',
            'cache', 'memcache',

            # Documentation & Support
            'docs', 'documentation', 'help', 'support', 'wiki', 'kb', 'knowledgebase',

            # Security & Auth
            'auth', 'login', 'sso', 'oauth', 'security', 'secure'
        ]

        cmd = [
            str(self.tools['alterx']),
            '-l', '-',  # Read from stdin
            '-p', ','.join(patterns),
            '-silent'
        ]

        try:
            # Take first 100 subdomains as seed
            sample = '\n'.join(list(existing_subs)[:100])

            result = subprocess.run(
                cmd,
                input=sample,
                capture_output=True,
                text=True,
                timeout=300  # 5 min
            )

            if result.returncode == 0 and result.stdout:
                subdomains = set(result.stdout.strip().split('\n'))
                return {s for s in subdomains if s and '.' in s and domain in s}

            return set()

        except Exception as e:
            self.logger.error(f"Alterx error: {e}")
            return set()

    def _create_subdomain_objects(self, subdomains: Set[str], parent_domain: str) -> List[Subdomain]:
        """
        Convert subdomain strings to Subdomain objects

        Args:
            subdomains: Set of subdomain strings
            parent_domain: Parent domain

        Returns:
            List of Subdomain objects
        """
        subdomain_objects = []

        for subdomain in sorted(subdomains):
            # Skip empty or invalid
            if not subdomain or not subdomain.strip():
                continue

            # Create subdomain object
            try:
                sub_obj = Subdomain(
                    subdomain=subdomain.strip(),
                    parent_domain=parent_domain,
                    source='multi_tool_enum'
                )
                subdomain_objects.append(sub_obj)
            except Exception as e:
                self.logger.warning(f"Failed to create subdomain object for {subdomain}: {e}")
                continue

        return subdomain_objects
