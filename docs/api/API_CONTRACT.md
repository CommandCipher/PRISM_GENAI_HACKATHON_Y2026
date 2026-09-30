# API Contract
## Smart Guided Troubleshooting Engine

This document defines the interfaces between the major components
of the troubleshooting engine.

---

# 1. Request

## POST /api/v1/troubleshoot

### Input

```json
{
  "query": "My battery is draining really fast"
}