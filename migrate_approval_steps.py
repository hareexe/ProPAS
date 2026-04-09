import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).with_name("propas.db")


def migrate_approval_steps():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Ensure the approval_steps table exists before trying to update it.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS approval_steps (
            id INTEGER PRIMARY KEY,
            name VARCHAR(50) UNIQUE,
            step_order INTEGER UNIQUE
        )
    """)

    # Ensure steps 1-4 exist with their expected names.
    base_steps = [
        ("CAS", 1),
        ("OSA", 2),
        ("FINANCE", 3),
        ("VPAA", 4),
    ]
    for name, step_order in base_steps:
        cur.execute("SELECT id FROM approval_steps WHERE step_order = ?", (step_order,))
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE approval_steps SET name = ? WHERE id = ?", (name, row[0]))
        else:
            cur.execute(
                "INSERT INTO approval_steps (name, step_order) VALUES (?, ?)",
                (name, step_order),
            )

    # Step 5 must match the existing office account username.
    cur.execute("SELECT id FROM approval_steps WHERE step_order = 5")
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE approval_steps SET name = ? WHERE id = ?", ("VicePresident", row[0]))
    else:
        cur.execute(
            "INSERT INTO approval_steps (name, step_order) VALUES (?, ?)",
            ("VicePresident", 5),
        )

    # Step 6 is President. Reuse the existing row when present.
    cur.execute("SELECT id FROM approval_steps WHERE lower(name) = lower(?)", ("President",))
    row = cur.fetchone()
    if row:
        president_step_id = row[0]
        cur.execute("UPDATE approval_steps SET step_order = 6 WHERE id = ?", (president_step_id,))
    else:
        cur.execute(
            "INSERT INTO approval_steps (name, step_order) VALUES (?, ?)",
            ("President", 6),
        )
        president_step_id = cur.lastrowid

    inserted_rows = 0
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='proposals'")
    if cur.fetchone():
        proposal_ids = [row[0] for row in cur.execute("SELECT id FROM proposals").fetchall()]
        for proposal_id in proposal_ids:
            cur.execute(
                "SELECT 1 FROM document_approvals WHERE document_id = ? AND step_id = ?",
                (proposal_id, president_step_id),
            )
            if not cur.fetchone():
                cur.execute(
                    """
                    INSERT INTO document_approvals
                        (document_id, step_id, status, signed_name, remarks, approved_at, approved_by)
                    VALUES
                        (?, ?, 'pending', NULL, NULL, NULL, NULL)
                    """,
                    (proposal_id, president_step_id),
                )
                inserted_rows += 1

    conn.commit()

    print("Approval-step migration complete.")
    print(f"President approvals added: {inserted_rows}")
    print("Current steps:")
    for step in cur.execute("SELECT step_order, name FROM approval_steps ORDER BY step_order"):
        print(f"  {step[0]}. {step[1]}")

    conn.close()


if __name__ == "__main__":
    migrate_approval_steps()
