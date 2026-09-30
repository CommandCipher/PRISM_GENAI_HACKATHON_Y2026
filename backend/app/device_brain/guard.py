from __future__ import annotations
import re
from .catalog import DeviceCatalog
from .models import Goal

class ValidationGuard:
    def __init__(self,catalog:DeviceCatalog):
        self.catalog=catalog

    def validate(self,goal:Goal)->list[str]:
        errors=[]
        allowed=self.catalog.exact_deeplink_values()
        validation_allowed={v for r in self.catalog.deeplink_records() for v in [((r.get("validation") or {}).get("deeplink"))] if v}
        seen_critical=False
        for action in goal.actions:
            if action.category.value=="critical":
                seen_critical=True
            elif seen_critical:
                errors.append("critical action is not last")
            for group in action.stepGroups:
                if action.category.value=="manual" and group.actionableDeeplink:
                    errors.append(f"manual deeplink: {action.actionName}")
                if group.actionableDeeplink and group.actionableDeeplink.deeplink not in allowed:
                    errors.append(f"deeplink not in catalog: {action.actionName}")
                if group.validationDeeplink and group.validationDeeplink.deeplink not in validation_allowed:
                    errors.append(f"validation deeplink not in catalog: {action.actionName}")
                for step in group.steps:
                    if re.search(r"https?://|www\.",step,re.I):
                        errors.append(f"web URL leakage: {action.actionName}")
        return errors
