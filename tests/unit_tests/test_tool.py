##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Tool related tests.
"""
from pathlib import Path

from pytest import raises
from pytest_subprocess.fake_popen import FakePopen

from fab.category import Category
from fab.tools import CompilerSuiteTool, Tool


class TestTool:
    def test_constructor(self):
        """
        Tests the construction of Tool.
        """
        tool = Tool("gnu", "gfortran", Category.FORTRAN_COMPILER)
        assert str(tool) == "Tool - gnu: gfortran"
        assert tool.executable == Path("gfortran")
        assert tool.name == "gnu"
        assert tool.category == Category.FORTRAN_COMPILER
        assert tool.is_compiler

        linker = Tool("gnu", "gfortran", Category.LINKER)
        assert str(linker) == "Tool - gnu: gfortran"
        assert linker.executable == Path("gfortran")
        assert linker.name == "gnu"
        assert linker.category == Category.LINKER
        assert not linker.is_compiler

        # Check that a path is accepted
        mytool = Tool("MyTool", Path("/bin/mytool"))
        assert mytool.name == "MyTool"
        # A path should be converted to a string, since this
        # is later passed to the subprocess command
        assert mytool.executable == Path("/bin/mytool")
        assert mytool.category == Category.MISC

        # Check that if we specify no category, we get the default:
        misc = Tool("misc", "misc")
        assert misc.executable == Path("misc")
        assert misc.name == "misc"
        assert misc.category == Category.MISC

    def test_chance_exec_name(self):
        """
        Tests the executable path can be changed.
        """
        tool = Tool("gfortran", "gfortran", Category.FORTRAN_COMPILER)
        assert tool.executable == Path("gfortran")
        tool.change_exec_name("start_me_instead")
        assert tool.executable == Path("start_me_instead")

    def test_is_available(self, fake_process):
        """
        Tests tool availability check is working.
        """
        tool = Tool("gfortran", "gfortran",
                    Category.FORTRAN_COMPILER)
        fake_process.register(['gfortran', '--version'])
        assert tool.is_available
        assert tool.availability_argument == '--version'

    def test_is_not_available(self, fake_process):
        tool = Tool("gfortran", "gfortran",
                    Category.FORTRAN_COMPILER)
        fake_process.register(['gfortran', '--version'], returncode=0)
        fake_process.register(['gfortran', '--ops'], returncode=1)
        with raises(RuntimeError) as err:
            tool.run("--ops")
        assert str(err.value) == "Command failed with return code 1:\ngfortran --ops"

    def test_is_available_argument(self, fake_process):
        tool = Tool("gfortran", "gfortran",
                    Category.FORTRAN_COMPILER,
                    availability_argument="am_i_here")
        fake_process.register(['gfortran', 'am_i_here'], returncode=-1)
        assert not tool.is_available
        assert tool.availability_argument == "am_i_here"

    def test_tool_flags(self):
        """
        Tests tool argument management works.
        """
        tool = Tool("gfortran", "gfortran", Category.FORTRAN_COMPILER)
        # pylint: disable-next=use-implicit-booleaness-not-comparison
        assert tool.flags == []
        tool.add_flags("-a")
        assert tool.flags == ["-a"]
        tool.add_flags(["-b", "-c"])
        assert tool.flags == ["-a", "-b", "-c"]

    def test_run_no_error_no_args(self, fake_process):
        """
        Tests running a tool with no additional command-line arguments
        resulting in no error.
        """
        tool = Tool("gnu", "gfortran", Category.FORTRAN_COMPILER)
        fake_process.register(['gfortran', '--version'])
        fake_process.register(['gfortran'], returncode=0, stdout="123")
        assert tool.run(capture_output=True) == "123"
        fake_process.register(['gfortran'], returncode=0, stdout="123")
        assert tool.run(capture_output=False) is None

    def test_run_no_error_single_args(self, fake_process):
        """
        Tests running a tool with an additiona command-line argument
        resulting in no error.
        """
        tool = Tool("gnu", "gfortran", Category.FORTRAN_COMPILER)
        fake_process.register(['gfortran', '--version'])
        fake_process.register(['gfortran', 'a'], stdout="456")
        assert tool.run("a", capture_output=True) == "456"
        fake_process.register(['gfortran', 'a'], stdout="456")
        assert tool.run("a", capture_output=False) is None

    def test_run_no_error_with_multiple_args(self, fake_process):
        """
        Tests running a tool with two additional command-line arguments
        resulting in no error.
        """
        tool = Tool("gnu", "gfortran", Category.FORTRAN_COMPILER)
        fake_process.register(['gfortran', '--version'])
        fake_process.register(['gfortran', 'a', 'b'], stdout="789")
        assert tool.run(["a", "b"], capture_output=True) == "789"
        fake_process.register(['gfortran', 'a', 'b'], stdout="789")
        assert tool.run(["a", "b"], capture_output=False) is None

    def test_run_command_error(self, fake_process):
        """
        Tests run method when command fails.
        """
        tool = Tool("gnu", "gfortran", Category.FORTRAN_COMPILER)
        fake_process.register(['gfortran', '--version'])
        fake_process.register(['gfortran'], returncode=1,
                              stderr="Bad thing happened")
        with raises(RuntimeError) as err:
            tool.run()
        assert err.value.args[0] \
               == '\n'.join(["Command failed with return code 1:",
                             "gfortran",
                             "Bad thing happened"])

    def test_run_error_file_not_found(self, fake_process):
        """
        Tests run method when asked to invoke a non-existant executable.
        """
        def missing_tool(process: FakePopen):
            process.returncode = 1
            raise FileNotFoundError("Command not found")

        tool = Tool("does_not_exist", "does_not_exist",
                    Category.FORTRAN_COMPILER)
        fake_process.register(['does_not_exist', '--version'],
                              callback=missing_tool)
        fake_process.register(['does_not_exist'], callback=missing_tool)
        with raises(RuntimeError) as err:
            tool.run()
        assert str(err.value) == "Command 'does_not_exist' could not be executed."


class TestCompilerSuiteTool:
    def test_suite_tool(self):
        """
        Tests the object constructor.
        """
        tool = CompilerSuiteTool("gnu", "gfortran", "gnu",
                                 Category.FORTRAN_COMPILER)
        assert str(tool) == "CompilerSuiteTool - gnu: gfortran"
        assert tool.executable == Path("gfortran")
        assert tool.name == "gnu"
        assert tool.suite == "gnu"
        assert tool.category == Category.FORTRAN_COMPILER
