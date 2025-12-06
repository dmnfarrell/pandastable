import streamlit as st
import sqlite3
import os
import uuid
import html
from datetime import datetime

DB_FILE = "forum.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Create posts table
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
                    id TEXT PRIMARY KEY,
                    author TEXT,
                    title TEXT,
                    category TEXT,
                    content TEXT,
                    timestamp TEXT,
                    likes INTEGER DEFAULT 0
                )''')
    # Create replies table
    c.execute('''CREATE TABLE IF NOT EXISTS replies (
                    id TEXT PRIMARY KEY,
                    post_id TEXT,
                    author TEXT,
                    content TEXT,
                    timestamp TEXT,
                    FOREIGN KEY(post_id) REFERENCES posts(id)
                )''')
    conn.commit()
    conn.close()

def get_posts():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Fetch all posts
    c.execute("SELECT * FROM posts ORDER BY timestamp DESC")
    posts_rows = c.fetchall()

    # Fetch all replies
    c.execute("SELECT * FROM replies ORDER BY timestamp ASC")
    replies_rows = c.fetchall()

    conn.close()

    # Group replies by post_id
    replies_by_post = {}
    for r in replies_rows:
        reply = dict(r)
        pid = reply['post_id']
        if pid not in replies_by_post:
            replies_by_post[pid] = []
        replies_by_post[pid].append(reply)

    posts = []
    for row in posts_rows:
        post = dict(row)
        post['replies'] = replies_by_post.get(post['id'], [])
        posts.append(post)

    return posts

def add_post(author, title, category, content):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    new_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO posts (id, author, title, category, content, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
              (new_id, author, title, category, content, timestamp))
    conn.commit()
    conn.close()

def add_reply(post_id, author, content):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    new_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO replies (id, post_id, author, content, timestamp) VALUES (?, ?, ?, ?, ?)",
              (new_id, post_id, author, content, timestamp))
    conn.commit()
    conn.close()

def like_post(post_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE posts SET likes = likes + 1 WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()

def get_avatar(username):
    # Simple deterministic avatar color based on username
    if not username:
        return "#888888" # Gray for unknown/empty
    colors = ["#FF5733", "#33FF57", "#3357FF", "#FF33F6", "#33FFF6", "#F6FF33"]
    hash_val = sum(ord(c) for c in username)
    return colors[hash_val % len(colors)]

def render_forum():
    # Ensure DB is initialized
    init_db()

    st.title("DataPlot Studio Community Forum")
    st.markdown("""
    Welcome to the community!
    Here you can **report bugs**, **ask for help**, **request features**, **exchange ideas**, and **make friends**.
    """)

    if 'forum_username' not in st.session_state:
        st.session_state.forum_username = "Anonymous"

    with st.sidebar.expander("Forum Profile", expanded=True):
        st.session_state.forum_username = st.text_input("Your Username", st.session_state.forum_username)

    posts = get_posts()

    # Tabs for different activities
    tab1, tab2 = st.tabs(["Browse Topics", "New Topic"])

    with tab2:
        st.subheader("Create a New Topic")
        with st.form("new_topic_form"):
            title = st.text_input("Title")
            category = st.selectbox("Category", ["General", "Bug Report", "Feature Request", "Help Wanted", "Ideas", "Introductions"])
            content = st.text_area("Content")
            submitted = st.form_submit_button("Post Topic")

            if submitted:
                if not title or not content:
                    st.error("Please fill in both title and content.")
                else:
                    add_post(st.session_state.forum_username, title, category, content)
                    st.success("Topic posted successfully!")
                    st.rerun()

    with tab1:
        # Filter controls
        col1, col2 = st.columns([3, 1])
        with col1:
            search_query = st.text_input("Search topics...", "")
        with col2:
            category_filter = st.selectbox("Filter by Category", ["All", "General", "Bug Report", "Feature Request", "Help Wanted", "Ideas", "Introductions"])

        filtered_posts = posts
        if category_filter != "All":
            filtered_posts = [p for p in filtered_posts if p["category"] == category_filter]

        if search_query:
            filtered_posts = [p for p in filtered_posts if search_query.lower() in p["title"].lower() or search_query.lower() in p["content"].lower()]

        for post in filtered_posts:
            with st.container():
                # Card-like styling using markdown and columns
                st.markdown("---")
                p_col1, p_col2 = st.columns([1, 6])

                # Sanitize user input for HTML display
                safe_author = html.escape(post['author'])

                with p_col1:
                    av_color = get_avatar(post['author'])
                    initial = safe_author[0].upper() if safe_author else "?"
                    st.markdown(f"""
                    <div style="background-color:{av_color}; color:white; padding:10px; border-radius:50%; text-align:center; font-weight:bold; width: 50px; height: 50px; line-height: 30px; margin: auto;">
                        {initial}
                    </div>
                    <div style="text-align:center; font-size:0.8em; margin-top:5px;">{safe_author}</div>
                    """, unsafe_allow_html=True)

                with p_col2:
                    st.markdown(f"### {post['title']}")
                    st.caption(f"Category: {post['category']} | Posted: {post['timestamp']}")
                    st.markdown(post['content'])

                    # Interaction bar
                    i_col1, i_col2, i_col3 = st.columns([1, 1, 4])
                    if i_col1.button("👍 Like", key=f"like_{post['id']}"):
                         like_post(post['id'])
                         st.rerun()

                    st.write(f"{post.get('likes', 0)} Likes")

                    with st.expander(f"Replies ({len(post['replies'])})"):
                        for reply in post['replies']:
                            safe_reply_author = html.escape(reply['author'])
                            st.markdown(f"**{safe_reply_author}** ({reply['timestamp']}):")
                            st.markdown(reply['content'])
                            st.divider()

                        with st.form(f"reply_{post['id']}"):
                            reply_content = st.text_area("Write a reply...", height=100)
                            if st.form_submit_button("Reply"):
                                if reply_content:
                                    add_reply(post['id'], st.session_state.forum_username, reply_content)
                                    st.success("Reply posted!")
                                    st.rerun()
