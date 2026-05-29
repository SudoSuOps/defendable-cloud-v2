# SSO / SAML / OIDC Roadmap

Enterprise SSO is not enabled in v1. The RBAC foundation is now in place:

- `Organization`
- `User.role`: `owner | member`
- owner-only API key management
- owner-created invites
- invite-token onboarding into an existing organization

## Target Protocols

- OIDC first for Google Workspace, Microsoft Entra ID, and Okta.
- SAML 2.0 for enterprise IdPs that require it.
- SCIM later for automated provisioning/deprovisioning.

## Required Controls

- Domain verification before SSO enforcement.
- Break-glass owner account.
- JIT provisioning maps IdP groups to `owner` or `member`.
- Session revocation when IdP membership changes.
- Audit receipts for IdP config changes.

## Suggested Implementation

Add `org_identity_providers` and `org_domains` tables, then route `/auth/sso/start` and `/auth/sso/callback` through Authlib or WorkOS/Clerk/Auth0 depending on enterprise buyer requirements.
