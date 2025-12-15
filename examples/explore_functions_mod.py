import os
import re
import sys
from evm_cfg_builder.cfg.cfg import CFG

def extract_function_signatures(sol_text: str):
    """
    Extracts all Solidity function text signatures from the provided source text.
    Returns a list of strings like 'transfer(address,uint256)'.
    """

    # Regex matches lines like:
    # function transfer(address to, uint256 amount) public returns (bool)
    # function approve(address spender, uint256 amount);
    pattern = re.compile(
        r"""
        function\s+                              # 'function' keyword
        (?P<name>[A-Za-z_][A-Za-z0-9_]*)         # function name
        \s*
        \(
            (?P<params>[^)]*)                    # parameter list (everything until closing parenthesis)
        \)
        """,
        re.VERBOSE,
    )

    signatures = []
    for match in pattern.finditer(sol_text):
        name = match.group("name")
        params_raw = match.group("params").strip()

        # Normalize parameter types: remove variable names, keep only types
        if not params_raw:
            param_types = []
        else:
            # Split by comma, remove extra spaces, and keep only the type part
            params = [p.strip() for p in params_raw.split(",") if p.strip()]
            param_types = []
            for p in params:
                # Match a Solidity type pattern; keep the type only (ignore variable name)
                # Handles things like "uint256", "address[] memory recipients"
                t = re.match(r"([A-Za-z0-9_\[\]]+)", p)
                if t:
                    param_types.append(t.group(1))

        signature = f"{name}({','.join(param_types)})"
        signatures.append(signature)

    return signatures

if len(sys.argv) != 3:
    print("Usage python explore_functions.py contract.evm contract.sol")
    sys.exit(-1)
    
evm_path = sys.argv[1]
sol_path = sys.argv[2]

if not os.path.isfile(evm_path):
    print(f"Error: File not found: {evm_path}")
    sys.exit(1)

if not os.path.isfile(sol_path):
    print(f"Error: File not found: {sol_path}")
    sys.exit(1)

with open(evm_path, encoding="utf-8") as f:
    runtime_bytecode = f.read()

with open(sol_path, encoding="utf-8") as f:
    source = f.read()

source_text_sigs = extract_function_signatures(source)
cfg = CFG(runtime_bytecode, source_text_sigs)


for function in sorted(cfg.functions, key=lambda x: x.start_addr):
    print(f"Function {function.name}")
    # Each function may have a list of attributes
    # An attribute can be:
    # - payable
    # - view
    # - pure
    if sorted(function.attributes):
        print("\tAttributes:")
        for attr in function.attributes:
            print(f"\t\t-{attr}")

    print("\n\tBasic Blocks:")
    for basic_block in sorted(function.basic_blocks, key=lambda x: x.start.pc):
        # Each basic block has a start and end instruction
        # instructions are pyevmasm.Instruction objects
        print(f"\t- @{hex(basic_block.start.pc)}-{hex(basic_block.end.pc)}")

        print("\t\tInstructions:")
        for ins in basic_block.instructions:
            print(f"\t\t- {ins.name}")

        # Each Basic block has a list of incoming and outgoing basic blocks
        # A basic block can be shared by different functions
        # And the list of incoming/outgoing basic blocks depends of the function
        # incoming_basic_blocks(function_key) returns the list for the given function
        print("\t\tIncoming basic_block:")
        for incoming_bb in sorted(
            basic_block.incoming_basic_blocks(function.key), key=lambda x: x.start.pc
        ):
            print(f"\t\t- {incoming_bb}")

        print("\t\tOutgoing basic_block:")
        for outgoing_bb in sorted(
            basic_block.outgoing_basic_blocks(function.key), key=lambda x: x.start.pc
        ):
            print(f"\t\t- {outgoing_bb}")
