"""
Tests for the framework detection module
"""

import sys
import os
import pytest
from pathlib import Path
import tempfile
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.artifactminer.RepositoryIntelligence.framework_detector import (
    detect_frameworks,
    detect_python_frameworks,
    detect_javascript_frameworks,
    detect_java_frameworks,
    detect_go_frameworks,
)


class TestPythonFrameworkDetection:
    """Test Python framework detection"""

    def test_detect_django_from_requirements(self):
        """Test Django detection from requirements.txt"""
        with tempfile.TemporaryDirectory() as tmpdir:
            req_file = Path(tmpdir) / "requirements.txt"
            req_file.write_text("django==4.2.0\nrequests==2.28.0\n")
            frameworks = detect_python_frameworks(tmpdir)
            assert "Django" in frameworks

    def test_detect_flask_from_requirements(self):
        """Test Flask detection from requirements.txt"""
        with tempfile.TemporaryDirectory() as tmpdir:
            req_file = Path(tmpdir) / "requirements.txt"
            req_file.write_text("flask==2.3.0\nwerkzeug==2.3.0\n")
            frameworks = detect_python_frameworks(tmpdir)
            assert "Flask" in frameworks

    def test_detect_fastapi_from_requirements(self):
        """Test FastAPI detection from requirements.txt"""
        with tempfile.TemporaryDirectory() as tmpdir:
            req_file = Path(tmpdir) / "requirements.txt"
            req_file.write_text("fastapi==0.95.0\nuvicorn==0.21.0\n")
            frameworks = detect_python_frameworks(tmpdir)
            assert "FastAPI" in frameworks

    def test_detect_pytest_from_requirements(self):
        """Test Pytest detection from requirements.txt"""
        with tempfile.TemporaryDirectory() as tmpdir:
            req_file = Path(tmpdir) / "requirements.txt"
            req_file.write_text("pytest==7.3.0\npytest-cov==4.1.0\n")
            frameworks = detect_python_frameworks(tmpdir)
            assert "Pytest" in frameworks

    def test_detect_sqlalchemy_from_requirements(self):
        """Test SQLAlchemy detection from requirements.txt"""
        with tempfile.TemporaryDirectory() as tmpdir:
            req_file = Path(tmpdir) / "requirements.txt"
            req_file.write_text("sqlalchemy==2.0.0\npsycopg2==2.9.0\n")
            frameworks = detect_python_frameworks(tmpdir)
            assert "SQLAlchemy" in frameworks

    def test_detect_from_pyproject_toml(self):
        """Test framework detection from pyproject.toml"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pyproject = Path(tmpdir) / "pyproject.toml"
            pyproject.write_text(
                "[project]\ndependencies = ['fastapi>=0.95.0', 'pydantic>=1.10.0']\n"
            )
            frameworks = detect_python_frameworks(tmpdir)
            assert "FastAPI" in frameworks
            assert "Pydantic" in frameworks

    def test_detect_from_pipfile(self):
        """Test framework detection from Pipfile"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pipfile = Path(tmpdir) / "Pipfile"
            pipfile.write_text("[packages]\ndjango = '*'\ncelery = '*'\n")
            frameworks = detect_python_frameworks(tmpdir)
            assert "Django" in frameworks
            assert "Celery" in frameworks

    def test_detect_from_setup_py(self):
        """Test framework detection from setup.py"""
        with tempfile.TemporaryDirectory() as tmpdir:
            setup = Path(tmpdir) / "setup.py"
            setup.write_text("install_requires=['flask', 'sqlalchemy']")
            frameworks = detect_python_frameworks(tmpdir)
            assert "Flask" in frameworks
            assert "SQLAlchemy" in frameworks

    def test_no_frameworks_in_empty_repo(self):
        """Test empty repository returns no frameworks"""
        with tempfile.TemporaryDirectory() as tmpdir:
            frameworks = detect_python_frameworks(tmpdir)
            assert frameworks == []


class TestJavaScriptFrameworkDetection:
    """Test JavaScript/TypeScript framework detection"""

    def test_detect_react(self):
        """Test React detection from package.json"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg = Path(tmpdir) / "package.json"
            pkg.write_text(
                json.dumps(
                    {
                        "dependencies": {"react": "^18.0.0", "react-dom": "^18.0.0"},
                        "devDependencies": {"webpack": "^5.0.0"},
                    }
                )
            )
            frameworks = detect_javascript_frameworks(tmpdir)
            assert "React" in frameworks

    def test_detect_vue(self):
        """Test Vue detection from package.json"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg = Path(tmpdir) / "package.json"
            pkg.write_text(json.dumps({"dependencies": {"vue": "^3.0.0"}}))
            frameworks = detect_javascript_frameworks(tmpdir)
            assert "Vue" in frameworks

    def test_detect_angular(self):
        """Test Angular detection from package.json"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg = Path(tmpdir) / "package.json"
            pkg.write_text(
                json.dumps({"dependencies": {"@angular/core": "^15.0.0"}})
            )
            frameworks = detect_javascript_frameworks(tmpdir)
            assert "Angular" in frameworks

    def test_detect_express(self):
        """Test Express detection from package.json"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg = Path(tmpdir) / "package.json"
            pkg.write_text(json.dumps({"dependencies": {"express": "^4.18.0"}}))
            frameworks = detect_javascript_frameworks(tmpdir)
            assert "Express" in frameworks

    def test_detect_nextjs(self):
        """Test Next.js detection from package.json"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg = Path(tmpdir) / "package.json"
            pkg.write_text(json.dumps({"dependencies": {"next": "^13.0.0"}}))
            frameworks = detect_javascript_frameworks(tmpdir)
            assert "Next.js" in frameworks

    def test_detect_nestjs(self):
        """Test Nest.js detection from package.json"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg = Path(tmpdir) / "package.json"
            pkg.write_text(
                json.dumps({"dependencies": {"@nestjs/common": "^9.0.0"}})
            )
            frameworks = detect_javascript_frameworks(tmpdir)
            assert "Nest.js" in frameworks

    def test_detect_typescript(self):
        """Test TypeScript detection from devDependencies"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg = Path(tmpdir) / "package.json"
            pkg.write_text(
                json.dumps({"devDependencies": {"typescript": "^5.0.0"}})
            )
            frameworks = detect_javascript_frameworks(tmpdir)
            assert "TypeScript" in frameworks

    def test_detect_jest(self):
        """Test Jest detection from devDependencies"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg = Path(tmpdir) / "package.json"
            pkg.write_text(json.dumps({"devDependencies": {"jest": "^29.0.0"}}))
            frameworks = detect_javascript_frameworks(tmpdir)
            assert "Jest" in frameworks

    def test_detect_multiple_js_frameworks(self):
        """Test detection of multiple JavaScript frameworks"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg = Path(tmpdir) / "package.json"
            pkg.write_text(
                json.dumps(
                    {
                        "dependencies": {"react": "^18.0.0", "express": "^4.18.0"},
                        "devDependencies": {"webpack": "^5.0.0", "jest": "^29.0.0"},
                    }
                )
            )
            frameworks = detect_javascript_frameworks(tmpdir)
            assert "React" in frameworks
            assert "Express" in frameworks
            assert "Webpack" in frameworks
            assert "Jest" in frameworks

    def test_invalid_package_json(self):
        """Test handling of invalid package.json"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg = Path(tmpdir) / "package.json"
            pkg.write_text("invalid json {")
            frameworks = detect_javascript_frameworks(tmpdir)
            assert frameworks == []


class TestJavaFrameworkDetection:
    """Test Java framework detection"""

    def test_detect_spring_from_pom(self):
        """Test Spring detection from pom.xml"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pom = Path(tmpdir) / "pom.xml"
            pom.write_text(
                """
                <project>
                    <dependencies>
                        <dependency>
                            <groupId>org.springframework.boot</groupId>
                            <artifactId>spring-boot-starter-web</artifactId>
                        </dependency>
                    </dependencies>
                </project>
                """
            )
            frameworks = detect_java_frameworks(tmpdir)
            assert "Spring" in frameworks

    def test_detect_hibernate_from_pom(self):
        """Test Hibernate detection from pom.xml"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pom = Path(tmpdir) / "pom.xml"
            pom.write_text(
                """
                <project>
                    <dependencies>
                        <dependency>
                            <groupId>org.hibernate</groupId>
                            <artifactId>hibernate-core</artifactId>
                        </dependency>
                    </dependencies>
                </project>
                """
            )
            frameworks = detect_java_frameworks(tmpdir)
            assert "Hibernate" in frameworks

    def test_detect_junit_from_pom(self):
        """Test JUnit detection from pom.xml"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pom = Path(tmpdir) / "pom.xml"
            pom.write_text(
                """
                <project>
                    <dependencies>
                        <dependency>
                            <groupId>junit</groupId>
                            <artifactId>junit</artifactId>
                        </dependency>
                    </dependencies>
                </project>
                """
            )
            frameworks = detect_java_frameworks(tmpdir)
            assert "JUnit" in frameworks

    def test_detect_from_gradle(self):
        """Test framework detection from build.gradle"""
        with tempfile.TemporaryDirectory() as tmpdir:
            gradle = Path(tmpdir) / "build.gradle"
            gradle.write_text(
                """
                dependencies {
                    implementation 'org.springframework.boot:spring-boot-starter-web'
                    implementation 'org.hibernate:hibernate-core'
                    testImplementation 'junit:junit'
                }
                """
            )
            frameworks = detect_java_frameworks(tmpdir)
            assert "Spring" in frameworks
            assert "Hibernate" in frameworks
            assert "JUnit" in frameworks

    def test_detect_from_gradle_kts(self):
        """Test framework detection from build.gradle.kts"""
        with tempfile.TemporaryDirectory() as tmpdir:
            gradle_kts = Path(tmpdir) / "build.gradle.kts"
            gradle_kts.write_text(
                """
                dependencies {
                    implementation("org.springframework.boot:spring-boot-starter-web")
                    implementation("org.hibernate:hibernate-core")
                }
                """
            )
            frameworks = detect_java_frameworks(tmpdir)
            assert "Spring" in frameworks
            assert "Hibernate" in frameworks


class TestGoFrameworkDetection:
    """Test Go framework detection"""

    def test_detect_gin(self):
        """Test Gin detection from go.mod"""
        with tempfile.TemporaryDirectory() as tmpdir:
            go_mod = Path(tmpdir) / "go.mod"
            go_mod.write_text(
                """
                module example.com
                go 1.20
                require (
                    github.com/gin-gonic/gin v1.9.0
                )
                """
            )
            frameworks = detect_go_frameworks(tmpdir)
            assert "Gin" in frameworks

    def test_detect_echo(self):
        """Test Echo detection from go.mod"""
        with tempfile.TemporaryDirectory() as tmpdir:
            go_mod = Path(tmpdir) / "go.mod"
            go_mod.write_text(
                """
                module example.com
                go 1.20
                require (
                    github.com/labstack/echo/v4 v4.10.0
                )
                """
            )
            frameworks = detect_go_frameworks(tmpdir)
            assert "Echo" in frameworks

    def test_detect_fiber(self):
        """Test Fiber detection from go.mod"""
        with tempfile.TemporaryDirectory() as tmpdir:
            go_mod = Path(tmpdir) / "go.mod"
            go_mod.write_text(
                """
                module example.com
                go 1.20
                require (
                    github.com/gofiber/fiber/v2 v2.43.0
                )
                """
            )
            frameworks = detect_go_frameworks(tmpdir)
            assert "Fiber" in frameworks

    def test_detect_gorm(self):
        """Test GORM detection from go.mod"""
        with tempfile.TemporaryDirectory() as tmpdir:
            go_mod = Path(tmpdir) / "go.mod"
            go_mod.write_text(
                """
                module example.com
                go 1.20
                require (
                    gorm.io/gorm v1.25.0
                )
                """
            )
            frameworks = detect_go_frameworks(tmpdir)
            assert "GORM" in frameworks


class TestIntegratedFrameworkDetection:
    """Test the integrated detect_frameworks function"""

    def test_detect_all_languages_combined(self):
        """Test detection with frameworks from multiple languages"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Add Python framework
            req = tmpdir_path / "requirements.txt"
            req.write_text("django==4.2.0\n")

            # Add JavaScript framework
            pkg = tmpdir_path / "package.json"
            pkg.write_text(json.dumps({"dependencies": {"react": "^18.0.0"}}))

            # Add Java framework
            pom = tmpdir_path / "pom.xml"
            pom.write_text(
                """
                <project>
                    <dependencies>
                        <dependency>
                            <groupId>org.springframework.boot</groupId>
                            <artifactId>spring-boot-starter-web</artifactId>
                        </dependency>
                    </dependencies>
                </project>
                """
            )

            # Add Go framework
            go_mod = tmpdir_path / "go.mod"
            go_mod.write_text("module example.com\nrequire github.com/gin-gonic/gin v1.9.0\n")

            frameworks = detect_frameworks(tmpdir)

            assert "Django" in frameworks
            assert "React" in frameworks
            assert "Spring" in frameworks
            assert "Gin" in frameworks

    def test_no_duplicates_in_results(self):
        """Test that duplicate frameworks are not included"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Add the same framework multiple times
            req = tmpdir_path / "requirements.txt"
            req.write_text("fastapi==0.95.0\n")

            pyproject = tmpdir_path / "pyproject.toml"
            pyproject.write_text("dependencies = ['fastapi>=0.95.0']\n")

            frameworks = detect_frameworks(tmpdir)

            # FastAPI should only appear once
            assert frameworks.count("FastAPI") == 1

    def test_empty_repo(self):
        """Test empty repository returns empty list"""
        with tempfile.TemporaryDirectory() as tmpdir:
            frameworks = detect_frameworks(tmpdir)
            assert frameworks == []
