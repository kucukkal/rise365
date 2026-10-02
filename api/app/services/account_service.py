from sqlalchemy import text
from sqlalchemy.orm import Session


def delete_user_account(db: Session, user) -> None:
    """Permanently delete a user and everything that belongs to them."""
    uid = str(user.id)
    level_id = str(user.program_level_id) if user.program_level_id else None
    for sql in [
        "DELETE FROM event_completions WHERE user_id::text = :uid "
        "OR event_id IN (SELECT id FROM events WHERE user_id::text = :uid)",
        "DELETE FROM events WHERE user_id::text = :uid",
        "DELETE FROM task_completions WHERE user_id::text = :uid",
        "DELETE FROM user_tasks WHERE user_id::text = :uid",
        "DELETE FROM prayer_logs WHERE user_id::text = :uid",
        "DELETE FROM users WHERE id::text = :uid",
    ]:
        db.execute(text(sql), {"uid": uid})
    # Personal MyBuild level (MyRise_FirstLast) goes too, if nobody else uses it
    if level_id:
        db.execute(text(
            "DELETE FROM program_levels WHERE id::text = :lid "
            "AND level_type = 'myrise' AND description = 'Personal MyBuild level' "
            "AND NOT EXISTS (SELECT 1 FROM users WHERE program_level_id::text = :lid)"
        ), {"lid": level_id})
    db.commit()
    db.expire_all()
