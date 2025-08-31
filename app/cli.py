"""
Command Line Interface for LearnWords
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
import uvicorn
from rich.console import Console
from rich.table import Table
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.models import Base

# Initialize CLI app and console
cli = typer.Typer(
    name="learnwords",
    help="LearnWords - AI-powered Lesson Plan Generator",
    add_completion=False,
)
console = Console()

settings = get_settings()


@cli.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
    reload: bool = typer.Option(False, help="Enable auto-reload"),
    workers: int = typer.Option(1, help="Number of worker processes"),
    log_level: str = typer.Option("info", help="Log level"),
):
    """Start the LearnWords server"""
    console.print(f"🚀 Starting LearnWords server on {host}:{port}", style="green")
    
    if workers > 1 and reload:
        console.print("⚠️  Cannot use --reload with multiple workers", style="yellow")
        reload = False
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level=log_level,
    )


@cli.command()
def init_db():
    """Initialize the database"""
    console.print("🗄️  Initializing database...", style="blue")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        console.print("✅ Database initialized successfully", style="green")
    except Exception as e:
        console.print(f"❌ Database initialization failed: {e}", style="red")
        sys.exit(1)


@cli.command()
def check_db():
    """Check database connection and status"""
    console.print("🔍 Checking database connection...", style="blue")
    
    try:
        db = SessionLocal()
        
        # Test connection
        result = db.execute(text("SELECT 1"))
        result.fetchone()
        
        # Get table count
        tables_result = db.execute(text("""
            SELECT COUNT(*) as table_count 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        table_count = tables_result.fetchone()[0]
        
        # Get user count
        try:
            user_result = db.execute(text("SELECT COUNT(*) FROM users"))
            user_count = user_result.fetchone()[0]
        except Exception:
            user_count = "N/A (tables not created)"
        
        db.close()
        
        # Display results
        table = Table(title="Database Status")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Connection", "✅ Connected")
        table.add_row("Database URL", settings.database.database_url.split("@")[-1])  # Hide credentials
        table.add_row("Tables", str(table_count))
        table.add_row("Users", str(user_count))
        
        console.print(table)
        
    except Exception as e:
        console.print(f"❌ Database connection failed: {e}", style="red")
        sys.exit(1)


@cli.command()
def migrate():
    """Run database migrations"""
    console.print("🔄 Running database migrations...", style="blue")
    
    try:
        import subprocess
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True
        )
        console.print("✅ Migrations completed successfully", style="green")
        if result.stdout:
            console.print(result.stdout)
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Migration failed: {e}", style="red")
        if e.stderr:
            console.print(e.stderr, style="red")
        sys.exit(1)
    except FileNotFoundError:
        console.print("❌ Alembic not found. Please install alembic.", style="red")
        sys.exit(1)


@cli.command()
def create_user(
    email: str = typer.Option(..., prompt=True, help="User email"),
    username: str = typer.Option(..., prompt=True, help="Username"),
    password: str = typer.Option(..., prompt=True, hide_input=True, help="Password"),
    full_name: Optional[str] = typer.Option(None, help="Full name"),
    is_admin: bool = typer.Option(False, help="Create as admin user"),
):
    """Create a new user"""
    console.print(f"👤 Creating user {username} ({email})...", style="blue")
    
    try:
        from app.core.security import get_password_hash
        from app.models.user import User
        
        db = SessionLocal()
        
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.email == email) | (User.username == username)
        ).first()
        
        if existing_user:
            console.print("❌ User with this email or username already exists", style="red")
            sys.exit(1)
        
        # Create new user
        hashed_password = get_password_hash(password)
        new_user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            full_name=full_name,
            is_active=True,
            is_verified=is_admin,  # Admin users are auto-verified
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        console.print(f"✅ User created successfully with ID: {new_user.id}", style="green")
        
        if is_admin:
            console.print("👑 User created with admin privileges", style="yellow")
        
        db.close()
        
    except Exception as e:
        console.print(f"❌ User creation failed: {e}", style="red")
        sys.exit(1)


@cli.command()
def health():
    """Check application health"""
    console.print("🔍 Checking application health...", style="blue")
    
    import httpx
    
    try:
        # Check basic health endpoint
        response = httpx.get(f"http://localhost:{settings.server.port}/health")
        
        if response.status_code == 200:
            console.print("✅ Application is healthy", style="green")
            
            # Try detailed health check
            try:
                detailed_response = httpx.get(
                    f"http://localhost:{settings.server.port}/api/v1/health/health"
                )
                if detailed_response.status_code == 200:
                    health_data = detailed_response.json()
                    
                    table = Table(title="Health Check Details")
                    table.add_column("Service", style="cyan")
                    table.add_column("Status", style="green")
                    
                    for service_name, service_info in health_data.get("services", {}).items():
                        status = service_info.get("status", "unknown")
                        status_style = "green" if status == "healthy" else "red"
                        table.add_row(service_name.title(), f"[{status_style}]{status}")
                    
                    console.print(table)
                    
            except Exception:
                console.print("⚠️  Detailed health check not available", style="yellow")
                
        else:
            console.print(f"❌ Application health check failed: {response.status_code}", style="red")
            
    except httpx.ConnectError:
        console.print("❌ Cannot connect to application. Is it running?", style="red")
        console.print(f"   Try: learnwords serve --port {settings.server.port}", style="dim")
    except Exception as e:
        console.print(f"❌ Health check failed: {e}", style="red")


@cli.command()
def worker():
    """Start Celery worker"""
    console.print("👷 Starting Celery worker...", style="blue")
    
    try:
        import subprocess
        
        cmd = [
            "celery",
            "-A", "app.celery_app",
            "worker",
            "--loglevel=info",
            "--concurrency=2",
        ]
        
        subprocess.run(cmd, check=True)
        
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Worker failed to start: {e}", style="red")
        sys.exit(1)
    except FileNotFoundError:
        console.print("❌ Celery not found. Please install celery.", style="red")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n👋 Worker stopped", style="yellow")


@cli.command()
def config():
    """Show current configuration"""
    console.print("⚙️  Current Configuration", style="blue")
    
    table = Table()
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    # Safe settings to display (no secrets)
    safe_settings = {
        "Environment": settings.server.environment,
        "Debug": settings.server.debug,
        "Host": settings.server.host,
        "Port": settings.server.port,
        "Database": settings.database.database_url.split("@")[-1] if "@" in settings.database.database_url else settings.database.database_url,
        "AI Provider": settings.ai.ai_provider,
        "Storage Backend": settings.storage.storage_backend,
        "Max File Size": f"{settings.storage.max_file_size / 1024 / 1024:.1f} MB",
    }
    
    for key, value in safe_settings.items():
        table.add_row(key, str(value))
    
    console.print(table)


@cli.command()
def version():
    """Show version information"""
    try:
        import importlib.metadata
        version = importlib.metadata.version("learnwords")
    except Exception:
        version = "development"
    
    console.print(f"LearnWords v{version}", style="bold green")
    console.print("AI-powered Lesson Plan Generator", style="dim")


def main():
    """Main CLI entry point"""
    cli()


if __name__ == "__main__":
    main()
