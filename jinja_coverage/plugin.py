"""The Jinja2 coverage plugin."""

import os.path
import coverage.plugin
from jinja2 import Environment
from jinja2.loaders import FileSystemLoader
from pathlib import Path


class JinjaPlugin(coverage.plugin.CoveragePlugin):
    def __init__(self, options):
        self.template_directory = Path(options.get("template_directory")).absolute()
        self.environment = Environment(
            loader=FileSystemLoader(self.template_directory),
            extensions=[]
        )

    def is_included(self, filename):
        filename_path = Path(filename).absolute()
        return self.template_directory in filename_path.parents

    def file_tracer(self, filename):
        #if os.path.samefile(os.path.dirname(filename), self.template_directory):
        if self.is_included(filename):
            return FileTracer(filename, self.template_directory)

    def file_reporter(self, filename):
        #if os.path.samefile(os.path.dirname(filename), self.template_directory):
        if self.is_included(filename):
            return FileReporter(filename, self.environment)


class FileTracer(coverage.plugin.FileTracer):
    def __init__(self, filename, template_directory):
        self.metadata = {'filename': filename}
        self.template_directory = template_directory
        self.filename = Path(filename)
        self.relative_path = self.filename.relative_to(self.template_directory)
        self.relative_path_to_template = {}

    def source_filename(self):
        return self.metadata["filename"]

    def line_number_range(self, frame):
        lineno = -1
        env = frame.f_locals.get('environment')
        if env:
            # get relative from templates. Not always matches.
            #template_file = Path(frame.f_code.co_filename)
            relative_path = self.filename.relative_to(self.template_directory)
            if relative_path != self.relative_path:
                raise Exception("Did not match expectation")
            #template = env.get_template(os.path.basename(frame.f_code.co_filename))
            template = self.relative_path_to_template.get(relative_path, None)
            if template is None:
                template = env.get_template(str(relative_path))
                self.relative_path_to_template[relative_path] = template

            lineno = template.get_corresponding_lineno(frame.f_lineno)

        if lineno == 0:
            # Zeros should not be tracked, return -1 to skip them.
            lineno = -1
        return lineno, lineno


class FileReporter(coverage.plugin.FileReporter):
    def __init__(self, filename, environment):
        super(FileReporter, self).__init__(filename)
        self._source = None
        self.environment = environment

    def source(self):
        if self._source is None:
            with open(self.filename) as f:
                self._source = f.read()
        return self._source

    def lines(self):
        source_lines = set()
        # this is what Jinja2 does when parsing, however not sure
        # if we do it correctly b/c Jinja doesn't provide correct
        # mappings between compiled Python code and HTML template text
        tokens = self.environment._tokenize(self.source(), self.filename)

        for token in tokens:
            source_lines.add(token.lineno)

        return source_lines
