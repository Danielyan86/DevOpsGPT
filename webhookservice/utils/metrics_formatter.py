from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def format_timestamp(ts):
    """Format timestamp to human-readable format."""
    if isinstance(ts, str):
        return ts
    return datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M:%S")

def process_time_series_data(results):
    """Process time series data and return formatted summary."""
    if not results:
        return None, None
    
    series = results[0]
    metric_name = series["metric"].get("__name__", "unknown")
    values = series["values"]
    
    if not values:
        return None, None
        
    values_float = [float(v[1]) for v in values]
    if "bytes" in metric_name.lower():
        values_float = [v / 1024 / 1024 for v in values_float]
        unit = "MB"
    else:
        unit = ""
        
    min_value = min(values_float)
    max_value = max(values_float)
    avg_value = sum(values_float) / len(values_float)
    min_idx = values_float.index(min_value)
    max_idx = values_float.index(max_value)
    
    min_time = format_timestamp(values[min_idx][0])
    max_time = format_timestamp(values[max_idx][0])
    start_time = format_timestamp(values[0][0])
    end_time = format_timestamp(values[-1][0])
    
    summary_text = (
        f"*Time Series Summary:*\n"
        f"• Metric: `{metric_name}`\n"
        f"• Time Range: `{start_time}` to `{end_time}`\n"
        f"• Minimum: `{min_value:.2f} {unit}` at `{min_time}`\n"
        f"• Maximum: `{max_value:.2f} {unit}` at `{max_time}`\n"
        f"• Average: `{avg_value:.2f} {unit}`"
    )
    
    return summary_text, metric_name

def format_metrics_message(raw_metrics, dify_response, is_refresh=False):
    """Format metrics data into Slack message blocks."""
    formatted_message = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🔍 *System Health Report*{' (Refreshed)' if is_refresh else ''}",
            },
        }
    ]
    
    if raw_metrics.get("data", {}).get("resultType") == "matrix":
        results = raw_metrics["data"].get("result", [])
        summary_text, _ = process_time_series_data(results)
        
        if summary_text:
            formatted_message.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": summary_text,
                },
            })
        else:
            formatted_message.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "ℹ️ No values found in the time series data.",
                },
            })
    else:
        metric_fields = []
        if "cpu_usage" in raw_metrics:
            metric_fields.append({
                "type": "mrkdwn",
                "text": f"💻 *CPU Usage:*\n`{raw_metrics['cpu_usage']:.2f}%`",
            })
        if "memory_usage" in raw_metrics:
            metric_fields.append({
                "type": "mrkdwn",
                "text": f"💾 *Memory Usage:*\n`{raw_metrics['memory_usage'] / 1024 / 1024:.2f} MB`",
            })
            
        if metric_fields:
            formatted_message.extend([
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Current Metrics:*",
                    },
                },
                {
                    "type": "section",
                    "fields": metric_fields,
                },
            ])
            
        if "server_time" in raw_metrics:
            formatted_message.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"🕒 Server Time: `{raw_metrics['server_time']}`",
                    }
                ],
            })
    
    formatted_message.extend([
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "📊 *Analysis*",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": dify_response.get("analysis", "No analysis available").replace("**", "*"),
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🔄 Refresh",
                        "emoji": True,
                    },
                    "style": "primary",
                    "action_id": "refresh_metrics",
                }
            ],
        },
    ])
    
    return formatted_message 