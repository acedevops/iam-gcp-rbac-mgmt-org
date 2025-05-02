# Project Notes  
*Last updated: {{DATE}}*  

---  
## 📌 Quick Links  
- [Errors & Fixes](#-errors--fixes)  
- [Design Decisions](#-design-decisions)  
- [TODOs & Future Work](#-todos--future-work)  
- [Meeting Notes](#-meeting-notes)  

---  

## 🐞 Errors & Fixes  

### [2024-05-02] Workflow only working for main branch  
**Error**: 
  - google-github-actions/auth failed with: failed to generate Google Cloud federated token for //iam.googleapis.com/***: {"error":"unauthorized_client","error_description":"The given credential is rejected by the attribute condition."}

**Fix**: 
  - Update Condition CEL in Google Workload Identity Federation (WIF) to allow feature branch:
    From: assertion.repository_owner=='acedevops' && (attribute.ref =="refs/heads/main")
    To: assertion.repository_owner=='acedevops' && (attribute.ref =="refs/heads/main" || attribute.ref =="refs/heads/feature/rbac-manager_func")

**Lesson**: Always handle token expiry client-side.  

### [2024-05-02] Database Connection Drops  
**Error**: PostgreSQL idle timeout after 5 minutes.  
**Fix**: Set `pool_min_conn: 1` in config.  
**Reference**: [Issue #45](https://github.com/your/repo/issues/45)  

---  

## 🎨 Design Decisions  

### [2024-05-01] API Pagination  
**Decision**: Used cursor-based pagination over offset.  
**Why**: Better performance for large datasets.  
**Files**: `api/pagination.js`  

---  

## ✅ TODOs & Future Work  

### High Priority  
- [ ] Optimize SQL query in `reports.js` (see [Issue #72](https://github.com/your/repo/issues/72)).  
- [ ] Add rate-limiting to auth endpoints.  

### Low Priority  
- [ ] Migrate to React 18.  

---  

## 📅 Meeting Notes  

### [2024-05-01] Sprint Planning  
**Goals**:  
1. Finish user auth module.  
2. Fix database timeouts.  
**Action Items**:  
- @alice: Test refresh tokens.  
- @bob: Document API changes.  

---  

## 📂 File Structure  
```plaintext
repo/
  ├── NOTES.md          <-- You are here  
  ├── infrastructure/
  │   ├── definitions/       # Role Definition YAML files  
  │   └── assignments        # Role Assignment YAML files 
  └── docs/            # Additional docs  