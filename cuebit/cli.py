"""
Command-line interface for Cuebit prompt management.

This module provides a CLI for managing Cuebit prompts,
allowing users to create, list, update, and manage prompts
through a command-line interface.
"""

import argparse
import uvicorn
import subprocess
import os
import sys
import threading
import json
import re
from typing import List, Dict, Any, Optional
from pprint import pprint
from datetime import datetime

from cuebit.registry import PromptRegistry


class CuebitCLI:
    """Command-line interface for Cuebit."""
    
    def __init__(self):
        """Initialize the CLI."""
        self.registry = PromptRegistry()
        self.parser = self.create_parser()
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser with all commands."""
        parser = argparse.ArgumentParser(
            description="Cuebit - Prompt Versioning and Management CLI",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=r"""
            Examples:
            cuebit serve                              # Start the server and UI
            cuebit list projects                      # List all projects
            cuebit list prompts --project blog        # List prompts in project 'blog'
            cuebit create prompt --task summarize \   # Create a prompt
                --template "Summarize: {input}" \
                --project blog --tags "prod,gpt-4"
            cuebit set-alias 123abc summarizer-prod   # Set alias 'summarizer-prod' for prompt '123abc'
            cuebit render --alias summarizer-prod \   # Render a prompt
                --vars '{"input":"text to summarize"}'
            cuebit export --format json               # Export all prompts to JSON
            """
        )
        
        # Add a new argument for database location
        parser.add_argument("--db-path", type=str, 
                           help="Database URL (overrides CUEBIT_DB_PATH environment variable)")
        
        subparsers = parser.add_subparsers(dest="command", help="Command to execute")
        
        # serve command
        serve_parser = subparsers.add_parser("serve", help="Start Cuebit server and UI")
        serve_parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to")
        serve_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
        serve_parser.add_argument("--data-dir", type=str, help="Data directory for the server")
        
        # list command
        list_parser = subparsers.add_parser("list", help="List prompts or projects")
        list_subparsers = list_parser.add_subparsers(dest="list_type", help="Type to list")
        
        list_projects = list_subparsers.add_parser("projects", help="List all projects")
        
        list_prompts = list_subparsers.add_parser("prompts", help="List prompts")
        list_prompts.add_argument("--project", type=str, help="Filter by project")
        list_prompts.add_argument("--search", type=str, help="Search term")
        list_prompts.add_argument("--tags", type=str, help="Filter by tags (comma-separated)")
        
        # get command
        get_parser = subparsers.add_parser("get", help="Get a prompt by ID or alias")
        get_parser.add_argument("identifier", type=str, help="Prompt ID or alias")
        get_parser.add_argument("--by-alias", action="store_true", help="Look up by alias instead of ID")
        
        # create command
        create_parser = subparsers.add_parser("create", help="Create a prompt")
        create_subparsers = create_parser.add_subparsers(dest="create_type", help="Type to create")
        
        create_prompt = create_subparsers.add_parser("prompt", help="Create a new prompt")
        create_prompt.add_argument("--task", type=str, required=True, help="Task for this prompt")
        create_prompt.add_argument("--template", type=str, required=True, help="Prompt template text")
        create_prompt.add_argument("--project", type=str, help="Project to assign prompt to")
        create_prompt.add_argument("--tags", type=str, help="Tags (comma-separated)")
        create_prompt.add_argument("--meta", type=str, help="Metadata as JSON string")
        create_prompt.add_argument("--updated-by", type=str, help="User creating the prompt")
        
        # update command
        update_parser = subparsers.add_parser("update", help="Update a prompt")
        update_parser.add_argument("prompt_id", type=str, help="Prompt ID to update")
        update_parser.add_argument("--template", type=str, required=True, help="New prompt template text")
        update_parser.add_argument("--tags", type=str, help="New tags (comma-separated)")
        update_parser.add_argument("--meta", type=str, help="New metadata as JSON string")
        update_parser.add_argument("--updated-by", type=str, help="User updating the prompt")
        
        # set-alias command
        alias_parser = subparsers.add_parser("set-alias", help="Set an alias for a prompt")
        alias_parser.add_argument("prompt_id", type=str, help="Prompt ID to alias")
        alias_parser.add_argument("alias", type=str, help="Alias to set")
        alias_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing alias")
        
        # render command
        render_parser = subparsers.add_parser("render", help="Render a prompt with variables")
        render_parser.add_argument("--id", type=str, help="Prompt ID")
        render_parser.add_argument("--alias", type=str, help="Prompt alias")
        render_parser.add_argument("--vars", type=str, required=True, help="Variables as JSON string")
        
        # delete command
        delete_parser = subparsers.add_parser("delete", help="Delete a prompt, project, or task")
        delete_subparsers = delete_parser.add_subparsers(dest="delete_type", help="Type to delete")
        
        delete_prompt = delete_subparsers.add_parser("prompt", help="Delete a prompt")
        delete_prompt.add_argument("prompt_id", type=str, help="Prompt ID to delete")
        delete_prompt.add_argument("--hard", action="store_true", 
                                   help="Use hard delete instead of soft delete")
        
        delete_project = delete_subparsers.add_parser("project", help="Delete a project")
        delete_project.add_argument("project", type=str, help="Project name to delete")
        delete_project.add_argument("--hard", action="store_true", 
                                    help="Use hard delete instead of soft delete")
        
        delete_task = delete_subparsers.add_parser("task", help="Delete a task in a project")
        delete_task.add_argument("project", type=str, help="Project name")
        delete_task.add_argument("task", type=str, help="Task name")
        delete_task.add_argument("--hard", action="store_true", 
                                 help="Use hard delete instead of soft delete")
        
        # history command
        history_parser = subparsers.add_parser("history", help="Show version history")
        history_parser.add_argument("project", type=str, help="Project name")
        history_parser.add_argument("task", type=str, help="Task name")
        
        # compare command
        compare_parser = subparsers.add_parser("compare", help="Compare two prompt versions")
        compare_parser.add_argument("prompt_id_1", type=str, help="First prompt ID")
        compare_parser.add_argument("prompt_id_2", type=str, help="Second prompt ID")
        
        # export command
        export_parser = subparsers.add_parser("export", help="Export prompts")
        export_parser.add_argument("--project", type=str, help="Project to export (all if omitted)")
        export_parser.add_argument("--format", type=str, choices=["json", "yaml"], default="json", 
                                   help="Export format")
        export_parser.add_argument("--file", type=str, help="Output file (stdout if omitted)")
        
        # import command
        import_parser = subparsers.add_parser("import", help="Import prompts")
        import_parser.add_argument("file", type=str, help="File to import")
        import_parser.add_argument("--format", type=str, choices=["json", "yaml"], 
                                   help="Import format (detected from file extension if omitted)")
        import_parser.add_argument("--skip-existing", action="store_true", default=True, 
                                   help="Skip existing prompts")
        
        # stats command
        subparsers.add_parser("stats", help="Show registry statistics")
        
        # init command (new)
        init_parser = subparsers.add_parser("init", help="Initialize a prompt registry")
        init_parser.add_argument("--data-dir", type=str, help="Custom data directory for prompt registry")
        
        return parser
    
    def start_streamlit(self, streamlit_env=None):
        """Start the Streamlit UI in a separate thread."""
        # Find the dashboard path relative to the package
        import cuebit
        package_dir = os.path.dirname(cuebit.__file__)
        dashboard_path = os.path.join(package_dir, "..", "cuebit_dashboard.py")
        
        # If the file doesn't exist, try looking in the package directory
        if not os.path.exists(dashboard_path):
            dashboard_path = os.path.join(package_dir, "cuebit_dashboard.py")
        
        if not os.path.exists(dashboard_path):
            print(f"Warning: Couldn't find dashboard at {dashboard_path}")
            print(f"Package directory: {package_dir}")
            # Try to find in current directory as a fallback
            dashboard_path = "cuebit_dashboard.py"
        
        # Start the Streamlit process with the current environment including CUEBIT_DB_PATH
        env = os.environ.copy()
        if streamlit_env:
            env.update(streamlit_env)
            
        return subprocess.Popen(["streamlit", "run", dashboard_path], env=env)
    
    def serve(self, args):
        """Start the server and UI."""
        # Set up environment with correct database path if specified
        streamlit_env = None
        if args.db_path:
            os.environ["CUEBIT_DB_PATH"] = args.db_path
            streamlit_env = {"CUEBIT_DB_PATH": args.db_path}
            
        # Alternatively, if data_dir is specified, use that
        if args.data_dir:
            if not os.path.exists(args.data_dir):
                os.makedirs(args.data_dir, exist_ok=True)
            db_path = f"sqlite:///{os.path.join(args.data_dir, 'prompts.db')}"
            os.environ["CUEBIT_DB_PATH"] = db_path
            streamlit_env = {"CUEBIT_DB_PATH": db_path}
        
        print(f"Starting Cuebit server on http://{args.host}:{args.port}")
        print(f"Database URL: {self.registry.db_url}")
        print("Starting Streamlit UI...")
        
        # Start Streamlit in background
        streamlit_process = self.start_streamlit(streamlit_env)
        
        try:
            # Start FastAPI
            uvicorn.run("cuebit.server:app", host=args.host, port=args.port, reload=True)
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            # Clean up Streamlit process
            if streamlit_process:
                streamlit_process.terminate()
    
    def list_projects(self, args):
        """List all projects."""
        projects = self.registry.list_projects()
        if not projects:
            print("No projects found")
            return
        
        print("Projects:")
        for project in sorted(projects):
            print(f"- {project}")
    
    def list_prompts(self, args):
        """List prompts with filtering."""
        # Parse tag filter
        tag_filter = None
        if args.tags:
            tag_filter = [tag.strip() for tag in args.tags.split(",") if tag.strip()]
        
        if args.project:
            # List prompts for specific project
            prompts = self.registry.list_prompts_by_project(args.project)
            print(f"Prompts in project '{args.project}':")
        else:
            # List all prompts
            prompts, _ = self.registry.list_prompts(search_term=args.search, tag_filter=tag_filter)
            print("All prompts:")
        
        if not prompts:
            print("No prompts found")
            return
        
        # Group by project/task
        from collections import defaultdict
        projects_map = defaultdict(lambda: defaultdict(list))
        
        for p in prompts:
            project = p.project or "Unassigned"
            projects_map[project][p.task].append(p)
        
        # Display prompts
        for project_name in sorted(projects_map.keys()):
            print(f"\n📁 {project_name}")
            
            for task_name in sorted(projects_map[project_name].keys()):
                print(f"  └─ {task_name}")
                
                # Sort by version
                versions = sorted(projects_map[project_name][task_name], key=lambda x: x.version)
                
                for p in versions:
                    alias_str = f" (alias: {p.alias})" if p.alias else ""
                    tags = json.loads(p.tags or "[]")
                    tags_str = f" [{', '.join(tags)}]" if tags else ""
                    updated_by = f" by {p.updated_by}" if p.updated_by else ""
                    updated_at = p.updated_at.strftime("%Y-%m-%d")
                    
                    print(f"      v{p.version}{alias_str}{tags_str} - {updated_at}{updated_by}")
                    print(f"      ID: {p.prompt_id}")
    
    def get_prompt(self, args):
        """Get a prompt by ID or alias."""
        if args.by_alias:
            prompt = self.registry.get_prompt_by_alias(args.identifier)
            if not prompt:
                print(f"No prompt found with alias '{args.identifier}'")
                return
        else:
            prompt = self.registry.get_prompt(args.identifier)
            if not prompt:
                print(f"No prompt found with ID '{args.identifier}'")
                return
        
        # Display prompt details
        print(f"Prompt: {prompt.task} (v{prompt.version})")
        print(f"ID: {prompt.prompt_id}")
        print(f"Project: {prompt.project or 'Unassigned'}")
        if prompt.alias:
            print(f"Alias: {prompt.alias}")
        
        tags = json.loads(prompt.tags or "[]")
        if tags:
            print(f"Tags: {', '.join(tags)}")
        
        print(f"Created: {prompt.created_at}")
        print(f"Updated: {prompt.updated_at} by {prompt.updated_by or 'Unknown'}")
        
        if prompt.template_variables:
            print(f"Variables: {', '.join(['{' + v + '}' for v in prompt.template_variables])}")
        
        print("\nTemplate:")
        print("---")
        print(prompt.template)
        print("---")
        
        print("\nMetadata:")
        pprint(prompt.meta)
        
        # Get examples
        examples = self.registry.get_examples(prompt.prompt_id)
        if examples:
            print("\nExamples:")
            for i, ex in enumerate(examples):
                print(f"Example {i+1}: {ex.get('description', '')}")
                print("  Input: " + ex.get('input', '')[:50] + ('...' if len(ex.get('input', '')) > 50 else ''))
                print("  Output: " + ex.get('output', '')[:50] + ('...' if len(ex.get('output', '')) > 50 else ''))
    
    def create_prompt(self, args):
        """Create a new prompt."""
        # Parse tags
        tags = []
        if args.tags:
            tags = [tag.strip() for tag in args.tags.split(",") if tag.strip()]
        
        # Parse metadata
        meta = {}
        if args.meta:
            try:
                meta = json.loads(args.meta)
            except json.JSONDecodeError:
                print("Error: Invalid JSON in metadata")
                return
        
        # Create prompt
        prompt = self.registry.register_prompt(
            task=args.task,
            template=args.template,
            meta=meta,
            tags=tags,
            project=args.project,
            updated_by=args.updated_by
        )
        
        print(f"Prompt created successfully!")
        print(f"ID: {prompt.prompt_id}")
        print(f"Project: {prompt.project or 'Unassigned'}")
        print(f"Task: {prompt.task} (v{prompt.version})")
    
    def update_prompt(self, args):
        """Update a prompt."""
        # Parse tags
        tags = None
        if args.tags:
            tags = [tag.strip() for tag in args.tags.split(",") if tag.strip()]
        
        # Parse metadata
        meta = None
        if args.meta:
            try:
                meta = json.loads(args.meta)
            except json.JSONDecodeError:
                print("Error: Invalid JSON in metadata")
                return
        
        # Update prompt
        prompt = self.registry.update_prompt(
            prompt_id=args.prompt_id,
            new_template=args.template,
            meta=meta,
            updated_by=args.updated_by,
            tags=tags
        )
        
        if not prompt:
            print(f"Error: No prompt found with ID '{args.prompt_id}'")
            return
        
        print(f"Prompt updated successfully!")
        print(f"New version: v{prompt.version}")
        print(f"ID: {prompt.prompt_id}")
    
    def set_alias(self, args):
        """Set alias for a prompt."""
        prompt = self.registry.add_alias(
            prompt_id=args.prompt_id,
            alias=args.alias,
            overwrite=args.overwrite
        )
        
        if not prompt:
            print(f"Error: No prompt found with ID '{args.prompt_id}' or alias already exists")
            return
        
        print(f"Alias '{args.alias}' set for prompt {prompt.task} (v{prompt.version})")
    
    def render_prompt(self, args):
        """Render a prompt with variables."""
        # Check for ID or alias
        if not args.id and not args.alias:
            print("Error: Either --id or --alias must be specified")
            return
        
        # Get the prompt
        if args.alias:
            prompt = self.registry.get_prompt_by_alias(args.alias)
            if not prompt:
                print(f"Error: No prompt found with alias '{args.alias}'")
                return
        else:
            prompt = self.registry.get_prompt(args.id)
            if not prompt:
                print(f"Error: No prompt found with ID '{args.id}'")
                return
        
        # Parse variables
        try:
            variables = json.loads(args.vars)
        except json.JSONDecodeError:
            print("Error: Invalid JSON in variables")
            return
        
        # Render prompt
        rendered = self.registry.render_prompt(prompt.prompt_id, variables)
        
        print("Rendered Prompt:")
        print("---")
        print(rendered)
        print("---")
    
    def delete_prompt(self, args):
        """Delete a prompt."""
        if args.hard:
            success = self.registry.delete_prompt_by_id(args.prompt_id)
        else:
            success = self.registry.soft_delete_prompt(args.prompt_id)
        
        if not success:
            print(f"Error: No prompt found with ID '{args.prompt_id}'")
            return
        
        print(f"Prompt {args.prompt_id} {'permanently deleted' if args.hard else 'soft deleted'}")
    
    def delete_project(self, args):
        """Delete a project."""
        count = self.registry.delete_project(args.project, use_soft_delete=not args.hard)
        print(f"{count} prompts {'permanently deleted' if args.hard else 'soft deleted'} from project '{args.project}'")
    
    def delete_task(self, args):
        """Delete a task in a project."""
        count = self.registry.delete_prompts_by_project_task(
            args.project, args.task, use_soft_delete=not args.hard
        )
        print(f"{count} prompts {'permanently deleted' if args.hard else 'soft deleted'} from task '{args.task}' in project '{args.project}'")
    
    def show_history(self, args):
        """Show version history for a project/task."""
        history = self.registry.get_version_history(args.project, args.task)
        
        if not history:
            print(f"No history found for {args.project}/{args.task}")
            return
        
        print(f"Version history for {args.project}/{args.task}:")
        
        for p in sorted(history, key=lambda x: x.version):
            alias_str = f" (alias: {p.alias})" if p.alias else ""
            updated_by = f" by {p.updated_by}" if p.updated_by else ""
            updated_at = p.updated_at.strftime("%Y-%m-%d")
            
            print(f"v{p.version}{alias_str} - {updated_at}{updated_by}")
            print(f"  ID: {p.prompt_id}")
    
    def compare_prompts(self, args):
        """Compare two prompt versions."""
        comparison = self.registry.compare_versions(args.prompt_id_1, args.prompt_id_2)
        
        if "error" in comparison:
            print(f"Error: {comparison['error']}")
            return
        
        print("Template Differences:")
        print("---")
        for line in comparison["template_diff"]:
            if line.startswith("+"):
                # Green for additions
                print(f"\033[92m{line}\033[0m")
            elif line.startswith("-"):
                # Red for removals
                print(f"\033[91m{line}\033[0m")
            else:
                print(line)
        print("---")
        
        # Show metadata changes
        if any(comparison["meta_changes"].values()):
            print("\nMetadata Changes:")
            if comparison["meta_changes"]["added"]:
                print("  Added:")
                for key, value in comparison["meta_changes"]["added"].items():
                    print(f"    {key}: {value}")
            
            if comparison["meta_changes"]["removed"]:
                print("  Removed:")
                for key, value in comparison["meta_changes"]["removed"].items():
                    print(f"    {key}: {value}")
            
            if comparison["meta_changes"]["changed"]:
                print("  Changed:")
                for key, change in comparison["meta_changes"]["changed"].items():
                    print(f"    {key}: {change['from']} -> {change['to']}")
        
        # Show tag changes
        if comparison["tags_changes"]["added"] or comparison["tags_changes"]["removed"]:
            print("\nTag Changes:")
            if comparison["tags_changes"]["added"]:
                print(f"  Added: {', '.join(comparison['tags_changes']['added'])}")
            if comparison["tags_changes"]["removed"]:
                print(f"  Removed: {', '.join(comparison['tags_changes']['removed'])}")
        
        # Show variable changes
        if comparison["variables_changes"]["added"] or comparison["variables_changes"]["removed"]:
            print("\nVariable Changes:")
            if comparison["variables_changes"]["added"]:
                print(f"  Added: {', '.join(['{' + v + '}' for v in comparison['variables_changes']['added']])}")
            if comparison["variables_changes"]["removed"]:
                print(f"  Removed: {', '.join(['{' + v + '}' for v in comparison['variables_changes']['removed']])}")
    
    def export_prompts(self, args):
        """Export prompts to a file or stdout."""
        try:
            exported = self.registry.export_prompts(
                project=args.project,
                format=args.format
            )
            
            if not exported:
                print("No prompts to export")
                return
            
            if args.file:
                with open(args.file, "w") as f:
                    f.write(exported)
                print(f"Exported to {args.file}")
            else:
                print(exported)
        except Exception as e:
            print(f"Export error: {str(e)}")
    
    def import_prompts(self, args):
        """Import prompts from a file."""
        # Determine format if not specified
        format = args.format
        if not format:
            if args.file.endswith(".json"):
                format = "json"
            elif args.file.endswith(".yaml") or args.file.endswith(".yml"):
                format = "yaml"
            else:
                print("Error: Could not determine format from file extension. Use --format.")
                return
        
        try:
            with open(args.file, "r") as f:
                import_data = f.read()
            
            results = self.registry.import_prompts(
                data=import_data,
                format=format,
                skip_existing=args.skip_existing
            )
            
            if "error" in results:
                print(f"Import error: {results['error']}")
                return
            
            print(f"Import completed:")
            print(f"- Total: {results['total']}")
            print(f"- Imported: {results['imported']}")
            print(f"- Skipped: {results['skipped']}")
            print(f"- Errors: {results['errors']}")
            
            if results["error_details"]:
                print("\nError details:")
                for error in results["error_details"]:
                    print(f"- {error}")
        except Exception as e:
            print(f"Import error: {str(e)}")
    
    def show_stats(self, args):
        """Show registry statistics."""
        stats = self.registry.get_usage_stats()
        
        print("Cuebit Registry Statistics")
        print("=========================")
        print(f"Total prompts: {stats['total_prompts']}")
        print(f"Active prompts: {stats['active_prompts']}")
        print(f"Deleted prompts: {stats['deleted_prompts']}")
        print(f"Total projects: {stats['total_projects']}")
        print(f"Total tasks: {stats['total_tasks']}")
        print(f"Prompts with aliases: {stats['prompts_with_aliases']}")
        print(f"Total examples: {stats.get('total_examples', 0)}")
        print(f"Database URL: {self.registry.db_url}")
        
        if stats.get("average_template_length"):
            print(f"Average template length: {stats['average_template_length']:.1f} characters")
        
        if stats.get("most_active_projects"):
            print("\nMost active projects:")
            for project, count in stats["most_active_projects"]:
                print(f"- {project}: {count} prompts")
        
        if stats.get("top_tags"):
            print("\nMost used tags:")
            for tag, count in stats["top_tags"]:
                print(f"- {tag}: {count} prompts")
    
    def init_registry(self, args):
        """Initialize a new prompt registry."""
        if args.data_dir:
            if not os.path.exists(args.data_dir):
                os.makedirs(args.data_dir, exist_ok=True)
            db_path = f"sqlite:///{os.path.join(args.data_dir, 'prompts.db')}"
            os.environ["CUEBIT_DB_PATH"] = db_path
            self.registry = PromptRegistry(db_url=db_path)
            print(f"Initialized new registry at: {db_path}")
        else:
            print(f"Using default registry at: {self.registry.db_url}")
            
        # Confirm it's working by checking if we can connect to DB
        try:
            projects = self.registry.list_projects()
            print(f"Registry initialized with {len(projects)} projects")
        except Exception as e:
            print(f"Error initializing registry: {str(e)}")
            return
    
    def run(self):
        """Run the CLI with the given arguments."""
        args = self.parser.parse_args()
        
        # If db-path is specified, reinitialize the registry
        if hasattr(args, 'db_path') and args.db_path:
            self.registry = PromptRegistry(db_url=args.db_path)
            
        if args.command is None:
            self.parser.print_help()
            return
        
        # Execute the appropriate command
        if args.command == "serve":
            self.serve(args)
        elif args.command == "list":
            if args.list_type == "projects":
                self.list_projects(args)
            elif args.list_type == "prompts":
                self.list_prompts(args)
            else:
                print("Error: Missing list type (projects or prompts)")
        elif args.command == "get":
            self.get_prompt(args)
        elif args.command == "create":
            if args.create_type == "prompt":
                self.create_prompt(args)
            else:
                print("Error: Missing create type (prompt)")
        elif args.command == "update":
            self.update_prompt(args)
        elif args.command == "set-alias":
            self.set_alias(args)
        elif args.command == "render":
            self.render_prompt(args)
        elif args.command == "delete":
            if args.delete_type == "prompt":
                self.delete_prompt(args)
            elif args.delete_type == "project":
                self.delete_project(args)
            elif args.delete_type == "task":
                self.delete_task(args)
            else:
                print("Error: Missing delete type (prompt, project, or task)")
        elif args.command == "history":
            self.show_history(args)
        elif args.command == "compare":
            self.compare_prompts(args)
        elif args.command == "export":
            self.export_prompts(args)
        elif args.command == "import":
            self.import_prompts(args)
        elif args.command == "stats":
            self.show_stats(args)
        elif args.command == "init":
            self.init_registry(args)


def main():
    """Entry point for the CLI."""
    cli = CuebitCLI()
    cli.run()


if __name__ == "__main__":
    main()