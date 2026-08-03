# choosability-oracle — TEST ORACLE ONLY

Landon Rabern's WebGraphs compute libraries (.NET Core; Silverlight UI discarded),
retained here **only** as a differential-testing oracle for the Python
reimplementation in `empirical/konigsberg_empirical/coloring/`.

Retirement plan (see plan §7):
1. Build the .NET compute libraries; expose via subprocess.
2. Reimplement in Python.
3. Differential test: feed nauty-generated graphs to both, assert identical output.
4. Retirement bar: agreement across all graphs up to n=10 plus a sampled larger set.
5. **Delete this directory.** Tests then pin against recorded oracle outputs
   (tests/differential/fixtures).

BLOCKING (plan §7, §9): written reuse terms from the author must be resolved
before any ported algorithm lands. The project license depends on it.
