// Choosability oracle CLI — JSONL stdin/stdout + --selftest.
// Glue only: all solver logic lives in the Choosability library (landon-tools).
using System.Text.Json;
using System.Text.Json.Serialization;
using Choosability;
using Choosability.FixerBreaker.KnowledgeEngine;
using Choosability.FixerBreaker.KnowledgeEngine.Slim.Super;

namespace ChoosabilityOracle;

static class Program
{
    static int Main(string[] args)
    {
        if (args.Length > 0 && args[0] == "--selftest")
            return SelfTest.Run();
        if (args.Any(a => a == "--selftest"))
            return SelfTest.Run();

        var opts = new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
            DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        };

        string? line;
        while ((line = Console.ReadLine()) != null)
        {
            if (string.IsNullOrWhiteSpace(line))
                continue;
            try
            {
                var req = JsonSerializer.Deserialize<OracleRequest>(line, opts)
                    ?? throw new InvalidOperationException("null request");
                var resp = Oracle.Analyze(req);
                Console.WriteLine(JsonSerializer.Serialize(resp, opts));
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"oracle error: {ex.Message}");
                return 1;
            }
        }
        return 0;
    }
}

sealed class OracleRequest
{
    public int N { get; set; }
    public List<List<int>> Edges { get; set; } = new();
    public List<int> Sizes { get; set; } = new();
    public int MaxPot { get; set; }
}

sealed class OracleResponse
{
    public int TotalBoards { get; set; }
    public bool Win { get; set; }
    public bool? NearlyWin { get; set; }
}

static class Oracle
{
    public static OracleResponse Analyze(OracleRequest req)
    {
        if (req.Sizes.Count != req.N)
            throw new ArgumentException($"sizes length {req.Sizes.Count} != n={req.N}");

        var adjacent = new bool[req.N, req.N];
        foreach (var e in req.Edges)
        {
            if (e.Count != 2)
                throw new ArgumentException("each edge must be a pair");
            int u = e[0], v = e[1];
            if (u == v || u < 0 || v < 0 || u >= req.N || v >= req.N)
                throw new ArgumentException($"bad edge [{u},{v}] for n={req.N}");
            adjacent[u, v] = adjacent[v, u] = true;
        }

        var g = new Graph(adjacent);
        var template = new Template(req.Sizes.ToList());

        var mind = new SuperSlimMind(g) { MaxPot = req.MaxPot };
        bool win = mind.Analyze(template, null);
        int total = mind.TotalBoards;

        bool? nearly = null;
        if (!win)
        {
            var m2 = new SuperSlimMind(g)
            {
                MaxPot = req.MaxPot,
                OnlyConsiderNearlyColorableBoards = true,
            };
            nearly = m2.Analyze(template, null);
        }

        return new OracleResponse
        {
            TotalBoards = total,
            Win = win,
            NearlyWin = nearly,
        };
    }
}

static class SelfTest
{
    // MindTests.cs nearly column (strict nearly-colorable; see ADJUDICATION.md).
    // Use `oracle --selftest --strict` to assert these; plain `--selftest` same after patch.
    static readonly (string Name, int Total, bool Win, bool? Nearly)[] Cases =
    {
        ("P_4_good.graph", 28, false, true),
        ("P_4_bad.graph", 40, false, false),
        ("long_3_claw_very_good.graph", 2336, true, null),
        ("long_3_claw_good.graph", 3488, false, true),
        ("long_3_claw_bad.graph", 5216, false, false),
    };

    public static int Run()
    {
        bool strict = Environment.GetCommandLineArgs().Contains("--strict");
        _ = strict; // fingerprints always use MindTests column after the nearly patch

        var fixtures = FindFixturesDir();
        if (fixtures is null)
        {
            Console.Error.WriteLine(
                "selftest: cannot find tests/fixtures/rabern_graphs (run from repo root)");
            return 1;
        }

        int failures = 0;
        foreach (var (name, expectTotal, expectWin, expectNearly) in Cases)
        {
            var path = Path.Combine(fixtures, name);
            if (!File.Exists(path))
            {
                Console.Error.WriteLine($"FAIL {name}: missing {path}");
                failures++;
                continue;
            }

            var req = LoadDotGraph(path);
            var got = Oracle.Analyze(req);
            bool ok = got.TotalBoards == expectTotal
                && got.Win == expectWin
                && got.NearlyWin == expectNearly;
            if (ok)
            {
                Console.WriteLine(
                    $"OK   {name}: total={got.TotalBoards} win={got.Win} nearly={Fmt(got.NearlyWin)}");
            }
            else
            {
                Console.Error.WriteLine(
                    $"FAIL {name}: got total={got.TotalBoards} win={got.Win} nearly={Fmt(got.NearlyWin)}; "
                    + $"expected total={expectTotal} win={expectWin} nearly={Fmt(expectNearly)}");
                failures++;
            }
        }

        if (failures == 0)
        {
            Console.WriteLine("selftest: all 5 MindTests fingerprints match (strict nearly)");
            return 0;
        }
        Console.Error.WriteLine($"selftest: {failures} failure(s)");
        return 1;
    }

    static string Fmt(bool? v) => v is null ? "null" : v.Value.ToString().ToLowerInvariant();

    static string? FindFixturesDir()
    {
        var dir = new DirectoryInfo(Directory.GetCurrentDirectory());
        while (dir != null)
        {
            var candidate = Path.Combine(dir.FullName, "tests", "fixtures", "rabern_graphs");
            if (Directory.Exists(candidate))
                return candidate;
            dir = dir.Parent;
        }
        return null;
    }

    /// <summary>
    /// Parse WebGraphs .graph JSON the same way MindTests derives template sizes.
    /// </summary>
    static OracleRequest LoadDotGraph(string path)
    {
        using var doc = JsonDocument.Parse(File.ReadAllText(path));
        var root = doc.RootElement;
        var vertices = root.GetProperty("Vertices");
        int n = vertices.GetArrayLength();
        var labels = new int[n];
        for (int i = 0; i < n; i++)
            labels[i] = int.Parse(vertices[i].GetProperty("Label").GetString()!);

        var adjacent = new bool[n, n];
        var edgeList = new List<List<int>>();
        foreach (var e in root.GetProperty("Edges").EnumerateArray())
        {
            int u = e.GetProperty("IndexV1").GetInt32();
            int v = e.GetProperty("IndexV2").GetInt32();
            int mult = e.TryGetProperty("Multiplicity", out var m) ? m.GetInt32() : 1;
            if (mult <= 0)
                continue;
            adjacent[u, v] = adjacent[v, u] = true;
            edgeList.Add(new List<int> { u, v });
        }

        int potSize = labels.Max();
        var degrees = new int[n];
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++)
                if (adjacent[i, j])
                    degrees[i]++;

        var sizes = new List<int>(n);
        for (int v = 0; v < n; v++)
            sizes.Add(potSize + degrees[v] - labels[v]);

        return new OracleRequest
        {
            N = n,
            Edges = edgeList,
            Sizes = sizes,
            MaxPot = potSize,
        };
    }
}
