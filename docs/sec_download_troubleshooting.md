# SEC EDGAR Download Troubleshooting

## 403 Forbidden

The SEC blocks requests that lack a proper User-Agent or come from certain IP ranges.

### Fix 1: Set your real contact in config

Edit `config/config.yaml` and replace the placeholder:

```yaml
sec_user_agent: "Your Name your.email@university.edu"
```

SEC expects format: `CompanyOrProjectName ContactEmail@domain.com`

### Fix 2: Use environment variable (Colab)

In a notebook cell before running the pipeline:

```python
import os
os.environ["SEC_USER_AGENT"] = "Your Name your.email@university.edu"
```

### Fix 3: Colab / cloud IP blocking

The SEC may block requests from cloud providers (Google Colab, AWS, etc.). If you still get 403 after setting a valid User-Agent:

- **Run locally** on your laptop or desktop (residential IP)
- Or use **SEC bulk data** (FTP) during off-peak hours: https://www.sec.gov/edgar/searchedgar/accessing-edgar-data.htm

### Rate limits

SEC allows ~10 requests per second. The code uses ~5/sec with retries. If you see 429 (Too Many Requests), the retry logic will back off automatically.
