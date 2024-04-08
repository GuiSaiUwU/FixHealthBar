try:
    """
    Input can be either a folder or a .wad.client file or a .bin file
    Or even a fantome UwU
    """
    from io import BytesIO
    from sys import argv
    from os import path
    from zipfile import ZIP_DEFLATED, ZipFile
    from LtMAO.binfile import BIN, BINField, BINType
    from LtMAO.wadfile import WAD, WADChunk


    def compute_hash(s: str):
        """
        Generaters FN1a lowered hash from a string
        """
        if s.startswith("0x"):
            return s.removeprefix("0x")
        
        h = 0x811c9dc5 
        for b in s.encode('ascii').lower(): 
            h = ((h ^ b) * 0x01000193) % 0x100000000 
        return f"{h:08x}"


    class CACHED_BIN_HASHES(dict):
        """
        Simple class that stores our hashed strings without needing to manually make the hash to get it
        """
        def __getitem__(self, key):
            if key in self.keys():
                return super().__getitem__(key)
            else:
                super().__setitem__(key, compute_hash(key))
                return super().__getitem__(key)


    BIN_HASH = CACHED_BIN_HASHES()
   
    if len(argv) != 2:
        input('Make sure to drag and drop something into the .exe!')
        exit()

    inpt = argv[1].lower()

    def parse_bin(bin_file: BIN) -> BIN:
        UnitHealthBarStyle = BINField()
        UnitHealthBarStyle.hash = BIN_HASH["UnitHealthBarStyle"]
        UnitHealthBarStyle.type = BINType.U8
        UnitHealthBarStyle.data = 10

        HealthBarData = BINField()
        HealthBarData.hash = BIN_HASH['HealthBarData']
        HealthBarData.type = BINType.Embed
        HealthBarData.hash_type = BIN_HASH["CharacterHealthBarDataRecord"]
        HealthBarData.data = [UnitHealthBarStyle]
        for entry in bin_file.entries:
            if entry.type == BIN_HASH["SkinCharacterDataProperties"]:
                # while you can say to me that every skin bin nowdays has healthbar 9 I wont trust human stoopidity to have a skin without even 9
                has_healthbardata_flag = any(i.hash_type == BIN_HASH["CharacterHealthBarDataRecord"] for i in entry.data)

                if not has_healthbardata_flag:
                    # Appending a HealthBarData to SkinCharacterData
                    entry.data.append(HealthBarData)
                    print("Fixed by appending one HealthBarData with UnitHealthBarStyle inside UwU!")
                else:
                    for s_property in entry.data:
                        # Now we are inside SkinCharacterDataProperties properties
                        if s_property.hash_type == BIN_HASH["CharacterHealthBarDataRecord"]:
                            has_unithealth_flag = any(i.hash == BIN_HASH["UnitHealthBarStyle"] for i in s_property.data)
                            if has_unithealth_flag:
                                for inside_healthbar in s_property.data:
                                    if inside_healthbar.hash == BIN_HASH["UnitHealthBarStyle"]:
                                        print(f"Just changed the value from {inside_healthbar.data} to 10 UwU!")
                                        inside_healthbar.data = 10 # WoW magic changed the value to 10 omfg
                            else:
                                # Wtf you have HealthBarData but dont have UnitHealthBarStyle?
                                s_property.data.append(UnitHealthBarStyle)
                                print("Fixed one HealthBarData that didn't have UnitHealthBarStyle UwU!")
        return bin_file

    def parse_wad(wad_path: str) -> bytes:
        wad_file = WAD()
        wad_file.read(wad_path)
        chunk_datas = []
        chunk_hashes = []
        with wad_file.stream(wad_path, 'rb+') as bs:
            for chunk in wad_file.chunks:
                chunk.read_data(bs)
                if chunk.extension == 'bin':
                    try:
                        bin_file = BIN()
                        bin_file.read(path='', raw=chunk.data)
                        bin_file = parse_bin(bin_file)
                        chunk.data = bin_file.write(path='', raw=True)
                    except Exception:
                        print(f'File Hash: "{chunk.hash}" THROWN AN EXCEPTION')
                
                chunk_datas.append(chunk.data)
                chunk_hashes.append(chunk.hash)

        wad = WAD()
        wad.chunks = [WADChunk.default() for _ in range(len(chunk_hashes))]
        
        with wad.stream('', 'rb+', raw=wad.write('', raw=True)) as bs:
            for id, chunk in enumerate(wad.chunks):
                chunk.write_data(bs, id, chunk_hashes[id], chunk_datas[id], previous_chunks=(
                                    wad.chunks[i] for i in range(id)))
                chunk.free_data()
            final_bytes = bs.raw()

        return final_bytes

    def parse_fantome(fantome_path: str) -> None:
        with open(fantome_path, 'rb') as file:
            zip_file = ZipFile(file, 'r')
            zip_name_list = zip_file.namelist()

            has_bin_files_flag = False
            bins_dict, final_bins_dict = {}, {}
            for info in zip_file.infolist():
                if not info.is_dir():
                    if info.filename.lower().endswith('.bin'):
                        bins_dict[info.filename] = zip_file.read(info)
                        has_bin_files_flag = True

            if not has_bin_files_flag:
                # checking for .wad.client files if doesnt havae bin files inside
                if not any(x.lower().endswith('info.json') for x in zip_name_list) or \
                not any(x.lower().endswith('.wad.client') for x in zip_name_list):
                    print("The Zip File does not contains info.json or .wad.client files (it isn't a fantome)")
                    return
            
            wads_dict, final_wads_dict, extra_infos = {}, {}, {}  # "Path/To/Wad.wad" = WadBytes
            
            for name in zip_name_list:
                if name.lower().endswith('.wad.client'):
                    with zip_file.open(name, 'r') as f:
                        wads_dict[name] = f.read()
                else:
                    if name.lower().endswith('.bin'):
                        continue
                    with zip_file.open(name, 'r') as f:
                        extra_infos[name] = f.read()
        
        for bin_path, bin_byte in bins_dict.items():
            try:
                bin_file = BIN()
                bin_file.read(path='', raw=bin_byte)
                bin_file = parse_bin(bin_file)
                final_bins_dict[bin_path] = bin_file.write(path='', raw=True)
            except Exception:
                print(f"Bin File: {bin_path} THROWN AN EXCEPTION")

        for wad_name, wad_byte in wads_dict.items():
            wad = WAD()
            wad.read(path='blank-path', raw=wad_byte)
            chunk_datas = []
            chunk_hashes = []
            with wad.stream(path='', mode='', raw=wad_byte) as bs:
                for chunk in wad.chunks:
                    chunk.read_data(bs)
                    if chunk.extension == 'bin':
                        try:
                            bin_file = BIN()
                            bin_file.read(path='', raw=chunk.data)
                            bin_file = parse_bin(bin_file)
                            chunk.data = bin_file.write(path='', raw=True)
                        except Exception:
                            print(f'File Hash: "{chunk.hash}" THROWN AN EXCEPTION')
                    chunk_datas.append(chunk.data)
                    chunk_hashes.append(chunk.hash)
                    chunk.free_data()
            
            wad = WAD()
            wad.chunks = [WADChunk.default() for _ in range(len(chunk_hashes))]
            
            with wad.stream('', 'rb+', raw=wad.write('', raw=True)) as bs:
                for id, chunk in enumerate(wad.chunks):
                    chunk.write_data(bs, id, chunk_hashes[id], chunk_datas[id], previous_chunks=(
                                        wad.chunks[i] for i in range(id)))
                    chunk.free_data()
                        
                final_wads_dict[wad_name] = bs.raw()

        final_zip_buffer = BytesIO()
        final_zip_file = ZipFile(final_zip_buffer, 'w', ZIP_DEFLATED, False)

        for final_wad_name, final_wad_bytes in final_wads_dict.items():
            final_zip_file.writestr(final_wad_name, final_wad_bytes)
        for extra_name, extra_byte in extra_infos.items():
            final_zip_file.writestr(extra_name, extra_byte)
        for final_bin_name, final_bin_byte in final_bins_dict.items():
            final_zip_file.writestr(final_bin_name, final_bin_byte)

        zip_file.close()
        final_zip_file.close()

        with open(fantome_path, 'wb') as file:
            print(f"Writing Fantome: {fantome_path}")
            file.write(final_zip_buffer.getvalue())
            

    if path.isfile(inpt) and inpt.endswith('.bin'):
        # User are using a .bin file
        try:
            bin_file = BIN()
            bin_file.read(inpt)
            parse_bin(bin_file)
            print("Writing .bin file :D")
            bin_file.write(inpt)
            print("End of Script.")
        except Exception as e:
            print(e, '\nSomething went wrong lol uwu')
            input()

    elif path.isfile(inpt) and inpt.endswith('.wad.client'):
        # User are using a .wad file
        try:
            print(f"Parsing Wad: {inpt}...")
            wad_bytes = parse_wad(inpt)
            print("Writing .wad file :D")
            with open(inpt, 'wb') as f:
                f.write(wad_bytes)
        except Exception as e:
            print(e, '\nSomething went wrong lol uwu')
            input()

    elif path.isfile(inpt) and (inpt.endswith('.zip') or inpt.endswith('.fantome')):
        # User are using a fantome
        try:
            print(f"Parsing Fantome: {inpt}")
            parse_fantome(inpt)
            print("End of Script.")
        except Exception as e:
            print(e, '\nSomething went wrong lol uwu')
            input()

    elif path.isdir(inpt):
        # User are using a dir
        from os import walk
        found_bins = []
        found_wads = []
        found_fantomes = []
        print("Searching for Wads and Bins and Fantomes/Zips inside the desired folder.")
        
        for root, dirs, files in walk(inpt):
            for file in files:
                if file.lower().endswith('.bin'):
                    found_bins.append(path.join(root, file))
                elif file.lower().endswith('.wad.client'):
                    found_wads.append(path.join(root, file))
                elif file.lower().endswith('.fantome') or file.lower().endswith('.zip'):
                    found_fantomes.append(path.join(root, file))
        print(f'"Bins": {found_bins}\n"Wads": {found_wads}\n"Fantomes": {found_fantomes}\n')
       
        for bin_path in found_bins:
            try:
                print(f"Parsing Bin: {bin_path}...")
                bin_file = BIN()
                bin_file.read(bin_path)
                parse_bin(bin_file)
                print("Writing .bin file :D")
                bin_file.write(bin_path)
            except Exception:
                print(f"{bin_path} THROWN AN EXCEPTION")
        
        for wad_path in found_wads:
            try:
                print(f"Parsing Wad: {wad_path}...")
                wad_bytes = parse_wad(wad_path)
                print("Writing .wad file :D")
                with open(wad_path, 'wb') as f:
                    f.write(wad_bytes)
            except Exception:
                print(f"{wad_path} THROWN AN EXCEPTION")

        for fantome_path in found_fantomes:
            try:
                print(f"Parsing Fantome: {fantome_path}")
                parse_fantome(fantome_path)
            except Exception:
                print(f"{fantome_path} THROWN AN EXCEPTION")

        print("End of Script.")

    else:
        print("Couldn't guess the desired object to fix uwu")
        input()
        
except Exception as e:
    print(e)
    print("\n something went wrong owo")
    input()