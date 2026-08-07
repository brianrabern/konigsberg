-- Konigsberg — formal tier root.
-- Import surface for the whole Lean library. Keep this thin: it just re-exports
-- the area roots so `import Konigsberg` pulls the library.
import Konigsberg.Foundations.Basic
import Konigsberg.Areas.Coloring.Basic
import Konigsberg.Areas.Coloring.Irreducible
import Konigsberg.Areas.Coloring.Orientation
import Konigsberg.Areas.Coloring.Kernel
import Konigsberg.Areas.Coloring.GraphPolynomial
import Konigsberg.Areas.Coloring.CliqueCollection
import Konigsberg.Areas.Coloring.Gallai
