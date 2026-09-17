export const rateLimitSchema = {
    title: 'Rate Limiting',
    description: 'Throttle outbound qBittorrent API calls and webhook/notification calls to avoid overwhelming qBittorrent or downstream services on large libraries.',
    fields: [
        {
            type: 'documentation',
            title: 'Rate Limiting Configuration Documentation',
            filePath: 'Config-Setup.md',
            section: 'rate_limit',
            defaultExpanded: false
        },
        {
            name: 'enabled',
            type: 'boolean',
            label: 'Enabled',
            description: 'Enable rate limiting for outbound qBittorrent API and webhook/notification calls. When disabled, no throttling is applied and existing behavior is unchanged.',
            default: false
        },
        {
            name: 'qbt_requests_per_second',
            type: 'number',
            label: 'qBittorrent Requests Per Second',
            description: 'Maximum sustained qBittorrent API requests per second.',
            default: 10,
            min: 1
        },
        {
            name: 'qbt_burst',
            type: 'number',
            label: 'qBittorrent Burst Size',
            description: 'Maximum burst size (token bucket capacity) for qBittorrent API requests.',
            default: 20,
            min: 1
        },
        {
            name: 'webhook_requests_per_second',
            type: 'number',
            label: 'Webhook Requests Per Second',
            description: 'Maximum sustained webhook/notification requests per second.',
            default: 5,
            min: 1
        },
        {
            name: 'webhook_burst',
            type: 'number',
            label: 'Webhook Burst Size',
            description: 'Maximum burst size (token bucket capacity) for webhook/notification requests.',
            default: 10,
            min: 1
        }
    ]
};
