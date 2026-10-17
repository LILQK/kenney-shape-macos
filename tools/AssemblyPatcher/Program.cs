using System.Security.Cryptography;
using Mono.Cecil;
using Mono.Cecil.Cil;

internal static class Program
{
    private const string SupportedHash = "64b5e7526638656c1766070690be30abcfebc18b02a20356bba2f103f7718a94";

    private static int Main(string[] args)
    {
        try
        {
            if (args.Length != 2)
                throw new ArgumentException("Usage: AssemblyPatcher <original.dll> <new-output.dll>");
            string input = Path.GetFullPath(args[0]);
            string output = Path.GetFullPath(args[1]);
            if (StringComparer.OrdinalIgnoreCase.Equals(input, output))
                throw new InvalidOperationException("The original assembly must not be overwritten.");
            if (File.Exists(output) || Directory.Exists(output))
                throw new InvalidOperationException("The output path already exists.");
            byte[] bytes = File.ReadAllBytes(input);
            if (Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant() != SupportedHash)
                throw new InvalidOperationException("Unsupported assembly. Expected the unmodified Linux 2.0.0 release.");

            using var resolver = new DefaultAssemblyResolver();
            resolver.AddSearchDirectory(Path.GetDirectoryName(input)!);
            using var stream = new MemoryStream(bytes, writable: false);
            using var assembly = AssemblyDefinition.ReadAssembly(stream, new ReaderParameters
            {
                AssemblyResolver = resolver,
                ReadSymbols = false,
                InMemory = true
            });
            var module = assembly.MainModule;
            if (assembly.Name.Name != "Assembly-CSharp" || assembly.Name.HasPublicKey)
                throw new InvalidOperationException("Unexpected assembly identity or signing state.");
            AddWorkingDirectoryFix(module);
            AddCommandModifier(module);
            Directory.CreateDirectory(Path.GetDirectoryName(output)!);
            using (var target = new FileStream(output, FileMode.CreateNew, FileAccess.Write))
                assembly.Write(target, new WriterParameters { WriteSymbols = false });
            Console.WriteLine("Applied macOS resource-directory and Command-key compatibility changes.");
            return 0;
        }
        catch (Exception error)
        {
            Console.Error.WriteLine(error.Message);
            return 1;
        }
    }

    private static MethodDefinition RequireMethod(ModuleDefinition module, string type, string method)
    {
        var owner = module.Types.Single(t => t.FullName == type);
        var found = owner.Methods.Single(m => m.Name == method && !m.HasParameters);
        if (!found.HasBody) throw new InvalidOperationException($"Missing method body: {type}.{method}");
        return found;
    }

    private static void AddWorkingDirectoryFix(ModuleDefinition module)
    {
        var awake = RequireMethod(module, "ProjectManager", "Awake");
        var application = module.GetTypeReferences().Single(t => t.FullName == "UnityEngine.Application");
        var path = new TypeReference("System.IO", "Path", module, module.TypeSystem.CoreLibrary);
        var directory = new TypeReference("System.IO", "Directory", module, module.TypeSystem.CoreLibrary);
        var getData = new MethodReference("get_dataPath", module.TypeSystem.String, application);
        var combine = new MethodReference("Combine", module.TypeSystem.String, path);
        combine.Parameters.Add(new ParameterDefinition(module.TypeSystem.String));
        combine.Parameters.Add(new ParameterDefinition(module.TypeSystem.String));
        var exists = new MethodReference("Exists", module.TypeSystem.Boolean, directory);
        exists.Parameters.Add(new ParameterDefinition(module.TypeSystem.String));
        var setDirectory = new MethodReference("SetCurrentDirectory", module.TypeSystem.Void, directory);
        setDirectory.Parameters.Add(new ParameterDefinition(module.TypeSystem.String));

        var helper = new TypeDefinition("MacPortTools", "Compatibility",
            TypeAttributes.NotPublic | TypeAttributes.Abstract | TypeAttributes.Sealed,
            module.TypeSystem.Object);
        module.Types.Add(helper);
        var initialize = new MethodDefinition("SetResourceDirectory",
            MethodAttributes.Assembly | MethodAttributes.Static, module.TypeSystem.Void);
        helper.Methods.Add(initialize);
        var il = initialize.Body.GetILProcessor();
        var discard = Instruction.Create(OpCodes.Pop);
        il.Emit(OpCodes.Call, getData);
        il.Emit(OpCodes.Ldstr, "Resources");
        il.Emit(OpCodes.Call, combine);
        il.Emit(OpCodes.Dup);
        il.Emit(OpCodes.Call, exists);
        il.Emit(OpCodes.Brfalse, discard);
        il.Emit(OpCodes.Call, setDirectory);
        il.Emit(OpCodes.Ret);
        il.Append(discard);
        il.Emit(OpCodes.Ret);
        initialize.Body.MaxStackSize = 2;
        awake.Body.GetILProcessor().InsertBefore(awake.Body.Instructions[0],
            Instruction.Create(OpCodes.Call, initialize));
    }

    private static void AddCommandModifier(ModuleDefinition module)
    {
        var update = RequireMethod(module, "EventManager", "Update");
        var store = update.Body.Instructions.Single(i => i.OpCode == OpCodes.Stsfld &&
            i.Operand is FieldReference f && f.Name == "modifierControl");
        var field = (FieldReference)store.Operand;
        var getKey = update.Body.Instructions
            .Where(i => i.OpCode == OpCodes.Call)
            .Select(i => i.Operand).OfType<MethodReference>()
            .First(m => m.DeclaringType.FullName == "UnityEngine.Input" && m.Name == "GetKey");
        var il = update.Body.GetILProcessor();
        // Unity KeyCode.LeftCommand = 310; RightCommand = 309.
        Instruction[] extra = {
            Instruction.Create(OpCodes.Ldsfld, field),
            Instruction.Create(OpCodes.Ldc_I4, 310),
            Instruction.Create(OpCodes.Call, getKey),
            Instruction.Create(OpCodes.Or),
            Instruction.Create(OpCodes.Ldc_I4, 309),
            Instruction.Create(OpCodes.Call, getKey),
            Instruction.Create(OpCodes.Or),
            Instruction.Create(OpCodes.Stsfld, field)
        };
        var cursor = store;
        foreach (var instruction in extra)
        {
            il.InsertAfter(cursor, instruction);
            cursor = instruction;
        }
        update.Body.MaxStackSize = Math.Max(update.Body.MaxStackSize, 3);
    }
}
