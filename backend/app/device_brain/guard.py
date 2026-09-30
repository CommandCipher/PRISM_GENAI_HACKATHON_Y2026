from __future__ import annotations
import re
from .catalog import DeviceCatalog
from .models import Goal

class ValidationGuard:
    def __init__(self,catalog:DeviceCatalog): self.catalog=catalog

    def validate(self,goal:Goal)->list[str]:
        errors=[]
        allowed=self.catalog.exact_deeplink_values()
        critical_seen=False
        for a in goal.actions:
            if a.category=="critical": critical_seen=True
            elif critical_seen: errors.append("critical action is not last")
            if a.category=="manual" and a.actionableDeeplink: errors.append(f"manual deeplink: {a.actionName}")
            if a.category=="auto" and self.catalog.deeplinks and not a.actionableDeeplink:
                errors.append(f"no verified deeplink: {a.actionName}")
            if a.actionableDeeplink and (a.actionableDeeplink not in allowed):
                errors.append(f"deeplink not in catalog: {a.actionName}")
            for g in a.stepGroups:
                for s in g.steps:
                    if re.search(r"https?://|www\.|\[[^]]+\]\(https?://",s,re.I):
                        errors.append(f"web URL leakage: {a.actionName}")
        return errors
