from __future__ import annotations


def privacy_allowed(profile, request) -> tuple[bool, str]:
    required = (request.privacy_level or "any").lower()
    if required == "local" and profile.privacy != "local":
        return False, "local privacy is required but provider is external"
    return True, "privacy requirement satisfied"


def profile_matches(profile, request) -> tuple[bool, str]:
    missing = set(request.required_capabilities) - set(profile.capabilities)
    if missing:
        return False, f"missing capabilities: {', '.join(sorted(missing))}"
    if request.structured_output_required and not profile.structured_output:
        return False, "structured output is required"
    if profile.context_capacity < request.max_context:
        return False, "context exceeds provider capacity"
    return True, "capabilities and context fit"