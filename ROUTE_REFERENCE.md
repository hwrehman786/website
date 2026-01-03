# 📋 Complete Route Reference - All 52 Endpoints

## Authentication Routes (4)

| Route | Method | Purpose |
|-------|--------|---------|
| `/register` | GET, POST | User registration |
| `/login` | GET, POST | User login |
| `/logout` | GET | User logout |
| `/check_username` | GET | Check username availability |

---

## Main Content Routes (7)

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Home feed (all posts) |
| `/my_account` | GET, POST | User profile & settings |
| `/create_post` | GET, POST | Create new post |
| `/edit_post/<id>` | GET, POST | Edit existing post |
| `/delete_post/<id>` | POST | Delete post |
| `/post/<id>` | Implied GET | View single post (in feed) |
| `/trending` | GET | Most liked posts |

---

## Discovery & Search Routes (4)

| Route | Method | Purpose |
|-------|--------|---------|
| `/search` | GET | Search posts by keyword |
| `/tag/<tag>` | GET | View posts by tag |
| `/api/tags` | GET | Get all available tags |
| `/profile/<username>` | GET | View user profile |

---

## Following System Routes (5)

| Route | Method | Purpose |
|-------|--------|---------|
| `/follow/<user_id>` | POST | Follow a user |
| `/unfollow/<user_id>` | POST | Unfollow a user |
| `/followers` | GET | View your followers |
| `/following` | GET | View users you follow |
| `/remove_follower/<user_id>` | POST | Remove a follower |
| `/api/is_following/<user_id>` | GET | Check follow status |

---

## Likes (Engagement) Routes (3)

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/like/<post_id>` | POST | Like a post |
| `/api/unlike/<post_id>` | POST | Unlike a post |
| `/api/is_liked/<post_id>` | GET | Check if user liked |

---

## Bookmarks Routes (3)

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/bookmark/<post_id>` | POST | Save post to bookmarks |
| `/api/unbookmark/<post_id>` | POST | Remove from bookmarks |
| `/api/is_bookmarked/<post_id>` | GET | Check bookmark status |
| `/bookmarks` | GET | View all bookmarks (paginated) |

---

## Analytics Routes (3)

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/track_view/<post_id>` | POST | Track post view |
| `/analytics` | GET | View analytics dashboard |
| `/api/post-stats/<post_id>` | GET | Get stats for single post |

---

## Comment & Reply Routes (3)

| Route | Method | Purpose |
|-------|--------|---------|
| `/comment/<post_id>` | POST | Add comment to post |
| `/api/reply/<comment_id>` | POST | Reply to comment (threaded) |
| `/delete_comment/<comment_id>` | POST | Delete comment |

---

## Notification Routes (5)

| Route | Method | Purpose |
|-------|--------|---------|
| `/notifications` | GET | View all notifications (paginated) |
| `/api/mark_notification_read/<id>` | POST | Mark single as read |
| `/api/mark_all_read` | POST | Mark all as read |
| `/api/notification/<id>` | DELETE | Delete notification |
| `/api/unread_count` | GET | Get count of unread |

---

## Direct Message Routes (4)

| Route | Method | Purpose |
|-------|--------|---------|
| `/messages` | GET | View inbox/conversations (paginated) |
| `/messages/<user_id>` | GET | View conversation with user |
| `/api/send_message/<recipient_id>` | POST | Send message to user |
| `/api/message/<message_id>` | DELETE | Delete message |

---

## User Blocking Routes (3)

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/block/<user_id>` | POST | Block a user |
| `/api/unblock/<user_id>` | POST | Unblock a user |
| `/blocked_users` | GET | View block list (paginated) |

---

## Collections Routes (6)

| Route | Method | Purpose |
|-------|--------|---------|
| `/collections` | GET | View all collections |
| `/api/create_collection` | POST | Create new collection |
| `/collection/<id>` | GET | View collection items (paginated) |
| `/api/add_to_collection/<col_id>/<post_id>` | POST | Add post to collection |
| `/api/remove_from_collection/<item_id>` | DELETE | Remove post from collection |
| `/api/collection/<id>` | DELETE | Delete entire collection |

---

## Recommendations Routes (1)

| Route | Method | Purpose |
|-------|--------|---------|
| `/recommendations` | GET | Get suggested users to follow |

---

## Dark Mode Routes (1)

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/toggle_dark_mode` | POST | Toggle dark mode preference |

---

## Sharing Routes (1)

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/share_post/<post_id>` | GET | Get share link/info |

---

## Debug Routes (2)

| Route | Method | Purpose |
|-------|--------|---------|
| `/debug/fix-posts` | GET | Fix posts with NULL timestamps |
| `/debug/publish-all` | GET | Publish all draft posts |

---

## Route Summary by Feature

### Feature 1: Following
- `/follow/<user_id>` - POST
- `/unfollow/<user_id>` - POST  
- `/followers` - GET
- `/following` - GET
- `/remove_follower/<user_id>` - POST
- `/api/is_following/<user_id>` - GET
**Total: 6 routes**

### Feature 2: Likes
- `/api/like/<post_id>` - POST
- `/api/unlike/<post_id>` - POST
- `/api/is_liked/<post_id>` - GET
**Total: 3 routes**

### Feature 3: Bookmarks
- `/api/bookmark/<post_id>` - POST
- `/api/unbookmark/<post_id>` - POST
- `/api/is_bookmarked/<post_id>` - GET
- `/bookmarks` - GET
**Total: 4 routes**

### Feature 4: Notifications
- `/notifications` - GET
- `/api/mark_notification_read/<id>` - POST
- `/api/mark_all_read` - POST
- `/api/notification/<id>` - DELETE
- `/api/unread_count` - GET
**Total: 5 routes**

### Feature 5: Direct Messages
- `/messages` - GET
- `/messages/<user_id>` - GET
- `/api/send_message/<recipient_id>` - POST
- `/api/message/<message_id>` - DELETE
**Total: 4 routes**

### Feature 6: Comments & Replies
- `/comment/<post_id>` - POST
- `/api/reply/<comment_id>` - POST
- `/delete_comment/<comment_id>` - POST
**Total: 3 routes**

### Feature 7: Blocking
- `/api/block/<user_id>` - POST
- `/api/unblock/<user_id>` - POST
- `/blocked_users` - GET
**Total: 3 routes**

### Feature 8: Collections
- `/collections` - GET
- `/api/create_collection` - POST
- `/collection/<id>` - GET
- `/api/add_to_collection/<col_id>/<post_id>` - POST
- `/api/remove_from_collection/<item_id>` - DELETE
- `/api/collection/<id>` - DELETE
**Total: 6 routes**

### Feature 9: Recommendations
- `/recommendations` - GET
**Total: 1 route**

### Feature 10: Analytics
- `/api/track_view/<post_id>` - POST
- `/analytics` - GET
- `/api/post-stats/<post_id>` - GET
**Total: 3 routes**

### Bonus: Dark Mode
- `/api/toggle_dark_mode` - POST
**Total: 1 route**

---

## HTTP Methods Used

| Method | Count | Purpose |
|--------|-------|---------|
| GET | 24 | Retrieve data, view pages |
| POST | 25 | Create/update data, perform actions |
| DELETE | 3 | Remove data |

---

## Response Formats

### HTML Pages
- `/register`, `/login`, `/`, `/my_account`, `/create_post`, `/edit_post/<id>`
- `/notifications`, `/messages`, `/messages/<user_id>`
- `/bookmarks`, `/trending`, `/profile/<username>`
- `/followers`, `/following`, `/blocked_users`
- `/collections`, `/recommendations`, `/analytics`
- `/search`, `/tag/<tag>`

### JSON Responses
- All `/api/*` routes return JSON
- Format: `{"success": true/false, "message": "...", "data": {...}}`

---

## Error Handling

All routes include:
- **404 errors** - Resource not found
- **403 errors** - Unauthorized access
- **400 errors** - Bad request/validation
- **500 errors** - Server errors (debug mode shows details)

---

## Testing Routes

### Test Following System
```
1. POST /follow/2 (as user 1)
2. GET /followers (check if user 2 sees user 1)
3. GET /following (check if user 1 sees user 2)
4. POST /unfollow/2 (unfollow)
```

### Test Likes
```
1. POST /api/like/1 (like post 1)
2. GET /api/is_liked/1 (verify like state)
3. POST /api/unlike/1 (unlike)
```

### Test Bookmarks
```
1. POST /api/bookmark/1 (save post 1)
2. GET /bookmarks (view bookmarks)
3. POST /api/unbookmark/1 (remove)
```

### Test Notifications
```
1. POST /follow/1 (triggers notification)
2. GET /notifications (view all notifications)
3. POST /api/mark_notification_read/1 (mark as read)
```

### Test Messages
```
1. POST /api/send_message/2 (send to user 2)
2. GET /messages (view conversations)
3. GET /messages/2 (view conversation)
4. DELETE /api/message/1 (delete message)
```

### Test Collections
```
1. POST /api/create_collection (create)
2. GET /collections (view all)
3. POST /api/add_to_collection/1/1 (add post)
4. DELETE /api/collection/1 (delete)
```

---

## Performance Notes

- All list routes support pagination (10-15 items/page)
- Use `?page=2` for pagination
- Database queries are optimized with lazy loading
- API responses are JSON for fast parsing

---

## Security Notes

- All routes except `/login`, `/register`, `/check_username` require login
- User ownership is verified on edit/delete operations
- Block list is enforced on messaging
- CSRF protection enabled on POST requests
- SQL injection protection via SQLAlchemy ORM

---

**Total Implemented Routes: 52**  
**Total Features: 10 + Dark Mode**  
**Status: All working ✅**

Visit http://127.0.0.1:5001 to start using!
