# Deployment Guide for Space Mission Design Assistant

## 🚀 Streamlit Cloud Deployment

### Prerequisites
- GitHub account
- Streamlit Cloud account (free tier available)
- OpenAI API key
- ChromaDB Cloud credentials

### Step 1: Prepare Repository

1. Fork or clone this repository to your GitHub account
2. Ensure all files are committed and pushed

### Step 2: Set Up Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Click "New app"
4. Select your repository and branch
5. Set main file path to: `streamlit_chatbot.py`

### Step 3: Configure Secrets

In Streamlit Cloud app settings, add the following secrets:

```toml
# OpenAI Configuration
OPENAI_API_KEY = "sk-proj-..."

# ChromaDB Cloud Configuration  
CHROMADB_API_KEY = "ck-..."
CHROMADB_TENANT = "your-tenant-id"
CHROMADB_DATABASE = "your-database-name"

# Authentication Secret
AUTH_SECRET_KEY = "generate-random-string-here"

# Database Configuration (optional - uses SQLite by default)
DATABASE_URL = "sqlite:///./space_mission_chat.db"
```

For production with PostgreSQL:
```toml
DATABASE_URL = "postgresql://username:password@host:port/dbname"
```

### Step 4: Deploy

1. Click "Deploy"
2. Wait for the app to build and start (usually 2-5 minutes)
3. Your app will be available at: `https://your-app-name.streamlit.app`

## 🔧 Local Development

### Setup

1. Clone the repository:
```bash
git clone https://github.com/JordanEmil/Mission-Design.git
cd Mission-Design
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.streamlit/secrets.toml`:
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit with your actual credentials
```

5. Run the app:
```bash
streamlit run streamlit_chatbot.py
```

## 📊 Database Options

### SQLite (Default)
- No configuration needed
- Good for development and small deployments
- Data persists in local file

### PostgreSQL (Recommended for Production)
1. Create a PostgreSQL database
2. Update `DATABASE_URL` in secrets
3. Tables are created automatically on first run

### Recommended Providers:
- Supabase (free tier available)
- Neon (free tier available)
- Railway
- Heroku Postgres

## 🔐 Security Best Practices

1. **Never commit secrets** to version control
2. **Use strong passwords** for database
3. **Rotate API keys** regularly
4. **Enable HTTPS** (automatic on Streamlit Cloud)
5. **Set up monitoring** for usage and errors

## 🎨 Customization

### Theme
Edit `.streamlit/config.toml` to customize colors and fonts

### Features
- Rate limiting: Adjust in `streamlit_chatbot.py` line ~150
- Session timeout: Configure in auth manager
- Export formats: Add new formats in export function

## 📈 Monitoring

### Streamlit Cloud Dashboard
- View app analytics
- Monitor resource usage
- Check error logs

### Custom Analytics
Add tracking code to `streamlit_chatbot.py`:
```python
# Example: Google Analytics
st.markdown("""
<script>
// Your analytics code here
</script>
""", unsafe_allow_html=True)
```

## 🆘 Troubleshooting

### Common Issues

1. **"Module not found" errors**
   - Check all dependencies in requirements.txt
   - Ensure versions are compatible

2. **"ChromaDB connection failed"**
   - Verify ChromaDB credentials
   - Check network connectivity

3. **"Database connection error"**
   - Verify DATABASE_URL format
   - Check database is accessible

4. **"Rate limit exceeded"**
   - Adjust rate limits in code
   - Consider upgrading OpenAI plan

### Debug Mode

Set in `.streamlit/config.toml`:
```toml
[logger]
level = "debug"
```

## 📱 Mobile Optimization

The app is mobile-responsive by default. For better mobile experience:
- Use collapsible sidebar
- Optimize message display
- Test on various screen sizes

## 🚀 Performance Optimization

1. **Caching**: Use `@st.cache_data` for expensive operations
2. **Lazy Loading**: Load history on demand
3. **Connection Pooling**: For database connections
4. **CDN**: Use for static assets

## 📄 License

This project is licensed under the MIT License.

## 🤝 Support

- GitHub Issues: [Report bugs](https://github.com/JordanEmil/Mission-Design/issues)
- Documentation: [Wiki](https://github.com/JordanEmil/Mission-Design/wiki)
- Author: Emil Ares

---

**Note**: Always test thoroughly before deploying to production!