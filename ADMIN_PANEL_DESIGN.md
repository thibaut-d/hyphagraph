# Admin Panel Design - User Management

**Date**: 2026-01-15
**Purpose**: Design administration panel for superuser access

---

## 1. Requirements

### User Management Features

**Must Have**:
- List all users (paginated table)
- View user details (email, role, status, created date)
- Activate/Deactivate users
- Promote/Demote to superuser
- Delete users
- User statistics (active, superuser, verified counts)

**Nice to Have**:
- Edit user email
- Force password reset
- View user activity (audit logs)
- Bulk operations

---

## 2. UI Layout

### Navigation
- Add "Admin" menu item (visible only to superusers)
- URL: `/admin`
- Icon: AdminPanelSettings or Shield

### Page Structure

```
┌────────────────────────────────────────────────────┐
│ HEADER                                             │
│ Administration Panel                               │
│ [Users] [System] [Audit Logs]                     │
└────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────┐
│ STATISTICS CARDS                                   │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│ │ Total   │ │ Active  │ │ Super   │ │ Verified│ │
│ │   5     │ │   4     │ │   2     │ │   3     │ │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘ │
└────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────┐
│ USERS TABLE                                        │
│                                                    │
│ Email             │ Role  │ Status │ Created  │Actions│
│ admin@example.com │ Super │ Active │ 2026-01  │ [Edit]│
│ user@example.com  │ User  │ Active │ 2026-01  │ [Edit]│
│ john@example.com  │ User  │Inactive│ 2025-12  │ [Edit]│
│                                                    │
│ [Create User]                                      │
└────────────────────────────────────────────────────┘
```

### User Detail Dialog/Drawer

```
┌────────────────────────────────────┐
│ User Details                       │
│                                    │
│ Email: user@example.com            │
│ Status: [x] Active                 │
│ Role: [ ] Superuser                │
│ Verified: [x] Email verified       │
│ Created: 2026-01-14                │
│                                    │
│ Actions:                           │
│ [Save Changes] [Delete User]       │
│ [Force Password Reset]             │
└────────────────────────────────────┘
```

---

## 3. API Endpoints Needed

### User Management (Superuser Only)

**List Users**:
```
GET /api/admin/users?limit=50&offset=0
Response: PaginatedResponse<UserRead>
```

**Get User**:
```
GET /api/admin/users/{user_id}
Response: UserRead
```

**Update User**:
```
PUT /api/admin/users/{user_id}
Body: {
  is_active: boolean,
  is_superuser: boolean,
  is_verified: boolean
}
```

**Delete User**:
```
DELETE /api/admin/users/{user_id}
```

**User Statistics**:
```
GET /api/admin/stats
Response: {
  total_users: 5,
  active_users: 4,
  superusers: 2,
  verified_users: 3
}
```

---

## 4. Security & Permissions

### Access Control
- Only superusers can access admin panel
- Check `current_user.is_superuser == true`
- Return 403 Forbidden if not superuser
- Frontend hides Admin menu if not superuser

### Restrictions
- Cannot delete yourself (prevent lockout)
- Cannot demote last superuser
- Cannot deactivate yourself
- Audit log all admin actions

---

## 5. Implementation Plan

### Backend (2-3 hours)
1. Create `backend/app/api/admin.py` router
2. Add user management endpoints (list, get, update, delete, stats)
3. Add superuser check dependency
4. Register router in main.py

### Frontend (2-3 hours)
1. Create `frontend/src/views/AdminView.tsx`
2. Create `frontend/src/components/UserManagementTable.tsx`
3. Create `frontend/src/components/UserEditDialog.tsx`
4. Add admin route to routes.tsx
5. Add Admin menu item (conditional on is_superuser)

### Testing (1 hour)
1. Test superuser access control
2. Test user CRUD operations
3. Test cannot delete self
4. Test audit logging

Total: 5-7 hours

---

## 6. Success Criteria

✅ Superusers can list all users
✅ Can activate/deactivate users
✅ Can promote/demote superusers
✅ Can delete users (with confirmation)
✅ Statistics cards show accurate counts
✅ Non-superusers cannot access
✅ Audit trail for all actions

