using System;
using System.Collections;
using System.IO;
using System.Linq;
using UnityEngine;
using Parabox.STL;

namespace MacPortTools.Tests
{
    public sealed class SmokeRunner : MonoBehaviour
    {
        public static void Initialize()
        {
            if (Environment.GetCommandLineArgs().Contains("--mac-port-test-output"))
                new GameObject("MacPortSmokeRunner").AddComponent<SmokeRunner>();
        }

        private IEnumerator Start()
        {
            yield return null;
            yield return null;
            int status = 0;
            string output = "";
            try
            {
                string[] args = Environment.GetCommandLineArgs();
                output = args[Array.IndexOf(args, "--mac-port-test-output") + 1];
                Directory.CreateDirectory(output);
                string expected = Path.GetFullPath(Path.Combine(Application.dataPath, "Resources"));
                if (Directory.GetCurrentDirectory() != expected)
                    throw new Exception("The resource-directory compatibility change did not run.");
                var browser = Crosstales.Common.Util.Singleton<Crosstales.FB.FileBrowser>.Instance;
                if (!browser.isPlatformSupported)
                    throw new Exception("The Cocoa file dialog adapter did not initialize.");

                int count = 0;
                foreach (string path in Directory.GetFiles("Samples", "*.kenshape", SearchOption.AllDirectories))
                {
                    Project.LoadPath(Path.GetFullPath(path));
                    if (Project.data.tiles.Length != Project.data.size.x * Project.data.size.y)
                        throw new Exception("Unexpected tile count: " + Path.GetFileName(path));
                    count++;
                }
                Project.LoadPath(Path.GetFullPath("Samples/bottle-potion.kenshape"));
                int colored = Project.data.tiles.Count(t => t.color >= 0);
                var position = new Vector2Int(0, 0);
                int previous = Project.GetTileColor(position);
                Project.SetTileColor(position, 1);
                if (Project.GetTileColor(position) != 1)
                    throw new Exception("Tile editing failed.");
                Project.SetTileColor(position, previous);
                Project.path = Path.Combine(output, "roundtrip.kenshape");
                Project.SaveFile();
                Project.LoadFile();
                if (Project.data.tiles.Count(t => t.color >= 0) != colored)
                    throw new Exception("Saved project contents changed.");
                ExportVector.Export(new Vector2(64, 64), 1, Path.Combine(output, "potion.svg"));

                var model = new GameObject("potion");
                Render.instance.Generate(model.transform);
                var meshes = model.GetComponentsInChildren<MeshFilter>();
                int vertices = meshes.Sum(m => m.sharedMesh.vertexCount);
                if (meshes.Length == 0 || vertices == 0)
                    throw new Exception("No model geometry was generated.");
                OBJExporter.Export(model.transform, false, false, output, "potion");
                if (!pb_Stl_Exporter.Export(Path.Combine(output, "potion.stl"), new[] { model }, FileType.Binary))
                    throw new Exception("STL export failed.");
                ProjectManager.instance.SetSaved();
                string report = $"PASS: {count} samples; resource directory; native adapter initialization; " +
                    $"tile editing; save/reload; SVG/OBJ/STL export; {meshes.Length} meshes; {vertices} source vertices.\n";
                File.WriteAllText(Path.Combine(output, "result.txt"), report);
                Debug.Log(report);
            }
            catch (Exception error)
            {
                status = 1;
                Debug.LogException(error);
                if (output != "") File.WriteAllText(Path.Combine(output, "result.txt"), "FAIL: " + error);
            }
            Application.Quit(status);
        }
    }
}
