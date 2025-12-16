#!/usr/bin/env python3
"""
Generate focused 50k wordlist for Shopify subdomain takeover detection

This wordlist is optimized for:
- E-commerce subdomains
- Shopify-specific patterns
- Common cloud service patterns
- Geographic variations
- Development/staging environments
"""

def generate_wordlist():
    """Generate comprehensive but focused wordlist"""
    words = set()

    # 1. E-commerce & Shopify-specific (highest priority)
    ecommerce_base = [
        'shop', 'store', 'checkout', 'cart', 'payment', 'billing', 'order', 'orders',
        'merchant', 'pos', 'retail', 'catalog', 'products', 'inventory', 'fulfillment',
        'shipping', 'returns', 'refund', 'customer', 'account', 'myaccount', 'profile',
        'wishlist', 'favorites', 'compare', 'search', 'browse', 'category', 'product',
        'deals', 'sale', 'promo', 'discount', 'coupon', 'gift', 'giftcard', 'voucher',
        'subscribe', 'subscription', 'membership', 'rewards', 'loyalty', 'points'
    ]

    #  2. Development & Environment
    env_prefixes = ['dev', 'staging', 'stage', 'prod', 'production', 'uat', 'qa', 'test', 'demo', 'sandbox', 'preview', 'temp']
    env_suffixes = ['', '1', '2', '3', '-old', '-new', '-v2', '-v3', '-backup']

    # 3. Admin & Management
    admin_terms = [
        'admin', 'administrator', 'management', 'console', 'dashboard', 'panel', 'control',
        'manager', 'portal', 'backend', 'backoffice', 'internal', 'staff', 'employee'
    ]

    # 4. API & Services
    api_terms = [
        'api', 'rest', 'graphql', 'ws', 'websocket', 'service', 'services', 'gateway',
        'endpoint', 'rpc', 'grpc', 'microservice', 'webhook', 'callback'
    ]
    api_versions = ['v1', 'v2', 'v3', 'v4', 'v5']

    # 5. Content & Media
    content_terms = [
        'cdn', 'static', 'assets', 'media', 'images', 'img', 'files', 'download', 'uploads',
        'content', 'resources', 'video', 'photo', 'gallery', 'blog', 'news', 'press'
    ]

    # 6. Geographic regions (for CDN/multi-region)
    regions = [
        'us', 'eu', 'uk', 'ca', 'au', 'asia', 'apac', 'emea', 'na', 'sa', 'af',
        'us-east', 'us-west', 'us-central', 'us-north', 'us-south',
        'eu-west', 'eu-east', 'eu-central', 'eu-north',
        'ap-southeast', 'ap-northeast', 'ap-south'
    ]

    # 7. Cloud & Infrastructure
    cloud_terms = [
        'aws', 'azure', 'gcp', 'cloud', 's3', 'blob', 'storage', 'bucket',
        'k8s', 'kubernetes', 'docker', 'container', 'cluster', 'node'
    ]

    # 8. Common subdomains
    common = [
        'www', 'www1', 'www2', 'www3', 'mail', 'email', 'smtp', 'pop', 'imap',
        'ftp', 'sftp', 'ssh', 'vpn', 'proxy', 'remote', 'login', 'auth', 'sso',
        'mobile', 'app', 'web', 'webapp', 'client', 'help', 'support', 'docs',
        'status', 'health', 'monitoring', 'metrics', 'logs', 'analytics'
    ]

    # Generate base words
    for word in ecommerce_base:
        words.add(word)
        # With numbers
        for i in range(1, 6):
            words.add(f"{word}{i}")
            words.add(f"{word}-{i}")
        # With common suffixes
        words.add(f"{word}-api")
        words.add(f"{word}-admin")
        words.add(f"{word}-cdn")
        words.add(f"{word}-static")

    # Environment combinations
    for env in env_prefixes:
        words.add(env)
        for suffix in env_suffixes:
            words.add(f"{env}{suffix}")
        # Env + base words
        for base in ['shop', 'store', 'api', 'admin', 'app', 'web']:
            words.add(f"{env}-{base}")
            words.add(f"{base}-{env}")

    # Admin variations
    for admin in admin_terms:
        words.add(admin)
        for i in range(1, 4):
            words.add(f"{admin}{i}")
        words.add(f"{admin}-panel")
        words.add(f"{admin}-portal")

    # API combinations
    for api in api_terms:
        words.add(api)
        for v in api_versions:
            words.add(f"{api}-{v}")
            words.add(f"{api}{v}")
        for base in ['shop', 'store', 'payment', 'checkout']:
            words.add(f"{api}-{base}")

    # Content delivery
    for content in content_terms:
        words.add(content)
        for i in range(1, 5):
            words.add(f"{content}{i}")

    # Geographic combinations
    for region in regions:
        words.add(region)
        for base in ['shop', 'store', 'cdn', 'api', 'app']:
            words.add(f"{region}-{base}")
            words.add(f"{base}-{region}")

    # Cloud combinations
    for cloud in cloud_terms:
        words.add(cloud)

    # Common subdomains
    for word in common:
        words.add(word)

    # Mobile & app variations
    mobile_terms = ['mobile', 'app', 'ios', 'android', 'm']
    for mobile in mobile_terms:
        words.add(mobile)
        words.add(f"{mobile}-shop")
        words.add(f"{mobile}-store")
        words.add(f"{mobile}-api")

    # Shopify-specific patterns
    shopify_patterns = [
        'shopify', 'myshopify', 'shopify-cdn', 'shopify-admin',
        'abandoned', 'abandoned-cart', 'abandoned-checkout',
        'collection', 'collections', 'variant', 'variants',
        'metafield', 'metafields', 'theme', 'themes', 'liquid',
        'storefront', 'pos-app', 'wholesale', 'b2b', 'plus'
    ]
    for pattern in shopify_patterns:
        words.add(pattern)

    # Security & Auth
    security_terms = ['auth', 'oauth', 'saml', 'sso', 'login', 'logout', 'signin', 'signout', 'register', 'signup']
    for sec in security_terms:
        words.add(sec)

    # Database & Cache (potential exposed services)
    db_terms = ['db', 'database', 'sql', 'mysql', 'postgres', 'mongodb', 'redis', 'cache', 'memcache']
    for db in db_terms:
        words.add(db)
        for i in range(1, 4):
            words.add(f"{db}{i}")

    # Monitoring & Logging
    monitor_terms = ['monitor', 'grafana', 'kibana', 'prometheus', 'datadog', 'newrelic', 'sentry']
    for mon in monitor_terms:
        words.add(mon)

    # Old/legacy/backup patterns (high takeover potential)
    legacy_terms = ['old', 'legacy', 'backup', 'archive', 'deprecated', 'inactive', 'unused']
    for legacy in legacy_terms:
        words.add(legacy)
        for base in ['shop', 'store', 'api', 'www', 'app']:
            words.add(f"{legacy}-{base}")
            words.add(f"{base}-{legacy}")

    # Marketing & campaigns
    marketing_terms = ['marketing', 'campaign', 'promo', 'landing', 'lp', 'newsletter', 'email', 'mailchimp']
    for mkt in marketing_terms:
        words.add(mkt)

    # Microservices (common in modern architectures)
    microservices = [
        'auth-service', 'payment-service', 'order-service', 'product-service',
        'user-service', 'notification-service', 'email-service', 'search-service',
        'recommendation-service', 'inventory-service', 'fulfillment-service'
    ]
    for ms in microservices:
        words.add(ms)

    # Additional common technical patterns
    tech_patterns = [
        'lb', 'loadbalancer', 'haproxy', 'nginx', 'apache', 'tomcat',
        'jenkins', 'gitlab', 'github', 'bitbucket', 'jira', 'confluence',
        'slack', 'mattermost', 'rocket', 'chat', 'team'
    ]
    for tech in tech_patterns:
        words.add(tech)

    return sorted(words)

def main():
    words = generate_wordlist()

    # Write to file
    output_file = '/Users/sayihhamza/Documents/Projects/subdomain-playground/data/wordlists/best-dns-wordlist.txt'

    with open(output_file, 'w') as f:
        for word in words:
            f.write(f"{word}\n")

    print(f"Generated {len(words)} words")
    print(f"Saved to: {output_file}")
    print(f"\nSample words (first 20):")
    for word in words[:20]:
        print(f"  {word}")
    print("\nSample words (e-commerce patterns):")
    ecommerce_words = [w for w in words if 'shop' in w or 'store' in w or 'checkout' in w][:20]
    for word in ecommerce_words:
        print(f"  {word}")

if __name__ == '__main__':
    main()
