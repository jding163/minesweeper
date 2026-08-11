pygame-ce 2.5.5 (SDL 2.32.6, Python 3.11.8)
done
{(2, 11): 13, (2, 12): 16, (2, 13): 13, (2, 14): 17, (2, 15): 21, (3, 11): 17, (3, 12): 16, (3, 13): 17, (3, 14): 15, (3, 15): 21}
total time: 25.25550389289856
Wrote profile results to main.py.lprof
Timer unit: 1e-06 s

Total time: 0 s
File: /Users/jeremyding/Desktop/projects/minesweeper/player.py
Function: play_game at line 129

Line #      Hits         Time  Per Hit   % Time  Line Contents
==============================================================
   129                                               @profile
   130                                               def play_game(self,seed=None):
   131                                                   #C.handle_keypress_n()  # full reset
   132                                                   self.board = Solver()
   133                                                   if self.timeout is not None:
   134                                                       self.board.deadline = time.time() + self.timeout
   135                                           
   136                                                   self.board.populate((0,0),seed=seed)
   137                                                   start_time = time.time()
   138                                           
   139                                                   self.board.reveal_tiles((0,0))
   140                                                   self.autoplay()
   141                                           
   142                                           
   143                                                   end_time = time.time()
   144                                                   duration = end_time - start_time
   145                                           
   146                                                   return {
   147                                                       'seed': seed,
   148                                                       'won': self.board.is_complete() and self.board.verify_win(),
   149                                                       'time': duration
   150                                                   }

Total time: 2.48641 s
File: /Users/jeremyding/Desktop/projects/minesweeper/solver.py
Function: solve_trivial_and_open at line 255

Line #      Hits         Time  Per Hit   % Time  Line Contents
==============================================================
   255                                               @profile
   256                                               def solve_trivial_and_open(self):
   257     14368       4049.0      0.3      0.2          init_mines = self.flag_count
   258     14368       4002.0      0.3      0.2          init_revealed = self.num_revealed
   259                                           
   260     14368    1693358.0    117.9     68.1          flags_found = self.flag_board()
   261     14368       4054.0      0.3      0.2          if flags_found:
   262     14368     768059.0     53.5     30.9              self.chord_board()
   263     14368       4001.0      0.3      0.2          new_mines = self.flag_count
   264     14368       3303.0      0.2      0.1          new_revealed = self.num_revealed
   265     14368       5581.0      0.4      0.2          return new_revealed != init_revealed or init_mines != new_mines

Total time: 3.13931 s
File: /Users/jeremyding/Desktop/projects/minesweeper/solver.py
Function: calc_probs_for_board at line 596

Line #      Hits         Time  Per Hit   % Time  Line Contents
==============================================================
   596                                               @profile
   597                                               def calc_probs_for_board(self,regions,groups_list,nonfrontier_locs,update_self=True):
   598      1490        464.0      0.3      0.0          safe_locs = []
   599      1490        385.0      0.3      0.0          mine_locs = []
   600      1490        832.0      0.6      0.0          total_sols_dict = defaultdict(int)
   601      1490        554.0      0.4      0.0          num_local_sols_at_count = defaultdict(int)
   602      1490        602.0      0.4      0.0          ps_with_num_mines = defaultdict(list)
   603      1490        603.0      0.4      0.0          mines_left = self.minecount-self.flag_count
   604                                           
   605                                           
   606      1490        397.0      0.3      0.0          safest_prob = 1
   607      1490        637.0      0.4      0.0          if len(regions)>0:
   608      1490    1519308.0   1019.7     48.4              ps = self.merge_all_possibilities(regions)
   609      1490      11199.0      7.5      0.4              ps = [p for p in ps if p.total_mines <= mines_left]
   610                                           
   611      1490        456.0      0.3      0.0              if update_self:
   612      1490       6606.0      4.4      0.2                  self.global_ps = ps
   613     75981      21668.0      0.3      0.7              for p in ps:
   614     74491      29124.0      0.4      0.9                  num_local_sols_at_count[p.total_mines] += p.num_cases
   615                                           
   616     74491      28363.0      0.4      0.9                  ps_with_num_mines[p.total_mines].append(p)
   617      1490        356.0      0.2      0.0              total_sols = 0
   618                                           
   619      6126       2526.0      0.4      0.1              for num_mines in ps_with_num_mines.keys():
   620      4636      11521.0      2.5      0.4                  total_sols_at_num_mines = num_local_sols_at_count[num_mines] * math.comb(len(nonfrontier_locs),mines_left-num_mines)
   621      4636       1326.0      0.3      0.0                  total_sols_dict[num_mines] = total_sols_at_num_mines
   622      4636       1509.0      0.3      0.0                  total_sols += total_sols_at_num_mines
   623      1490        395.0      0.3      0.0              if update_self:
   624      1490        595.0      0.4      0.0                  self.total_sols = total_sols
   625      1490        695.0      0.5      0.0                  self.total_sols_dict = total_sols_dict
   626                                                       # invalid board
   627      1490        401.0      0.3      0.0              if total_sols == 0:
   628                                                           return [],[],1,0
   629     26835       8420.0      0.3      0.3              for group_info in groups_list:
   630     25345       6418.0      0.3      0.2                  group_locs = group_info.tile_locs
   631     25345       6529.0      0.3      0.2                  rep_loc = group_locs[0]
   632     25345     794467.0     31.3     25.3                  prob_at_loc = self.calc_prob_at_loc(rep_loc,groups_list,nonfrontier_locs,total_sols,total_sols_dict,num_local_sols_at_count,ps_with_num_mines)
   633     62364      27733.0      0.4      0.9                  for loc in group_locs:
   634     37019       9202.0      0.2      0.3                      if update_self:
   635     37019      14004.0      0.4      0.4                          self.mine_probs[loc] = prob_at_loc
   636     37019       9919.0      0.3      0.3                      if prob_at_loc == 0:
   637       119         39.0      0.3      0.0                          safe_locs.append(loc)
   638     36900       9044.0      0.2      0.3                      elif prob_at_loc == 1:
   639       110         48.0      0.4      0.0                          mine_locs.append(loc)
   640     25345      11512.0      0.5      0.4                  safest_prob = min(safest_prob,prob_at_loc)
   641                                                   else:
   642                                                       total_sols = math.comb(len(nonfrontier_locs),mines_left)
   643                                                       if update_self:
   644                                                           self.total_sols = total_sols
   645                                                           self.total_sols_dict = {mines_left:total_sols}
   646                                           
   647      1490        637.0      0.4      0.0          if len(nonfrontier_locs) > 0:
   648                                                       
   649      1331        351.0      0.3      0.0              nf_loc = None
   650      1331        562.0      0.4      0.0              for nf_l in nonfrontier_locs:
   651      1331        339.0      0.3      0.0                  nf_loc = nf_l
   652      1331        370.0      0.3      0.0                  break
   653      1331      10220.0      7.7      0.3              prob_at_loc = self.calc_prob_at_loc(nf_loc,groups_list,nonfrontier_locs,total_sols,total_sols_dict,num_local_sols_at_count,ps_with_num_mines)
   654    410041     148141.0      0.4      4.7              for loc in nonfrontier_locs:
   655    408710      97823.0      0.2      3.1                  if update_self:
   656    408710     140112.0      0.3      4.5                      self.mine_probs[loc] = prob_at_loc
   657                                           
   658                                           
   659                                           
   660    408710     104106.0      0.3      3.3                  if prob_at_loc == 0:
   661        41         13.0      0.3      0.0                      safe_locs.append(loc)
   662    408669      97201.0      0.2      3.1                  elif prob_at_loc == 1:
   663                                                               mine_locs.append(loc)
   664      1331        751.0      0.6      0.0              safest_prob = min(safest_prob,prob_at_loc)
   665                                                   # print(safe_locs)
   666                                                   # print(mine_locs)
   667                                                   # print(safest_prob)
   668                                                   # print(total_sols)
   669      1490        824.0      0.6      0.0          return safe_locs,mine_locs,safest_prob,total_sols

Total time: 21.8854 s
File: /Users/jeremyding/Desktop/projects/minesweeper/solver.py
Function: solve_exhaustive at line 670

Line #      Hits         Time  Per Hit   % Time  Line Contents
==============================================================
   670                                               @profile
   671                                               def solve_exhaustive(self,force=False):
   672      3990       9316.0      2.3      0.0          self.mine_probs[:] = -1
   673      3990    1374187.0    344.4      6.3          self.regions_list = self.get_updated_regions_list()
   674      3990   15885669.0   3981.4     72.6          groups_list= self.find_possibilities(self.regions_list)
   675      3990       1373.0      0.3      0.0          ff_groups = []
   676      3990        972.0      0.2      0.0          ic_regions = []
   677      3990        867.0      0.2      0.0          ff_influence_locs = []
   678     13704       6041.0      0.4      0.0          for region in self.regions_list:
   679      9714      80148.0      8.3      0.4              ff_groups_in_region,ff_influence_locs_in_region = ffd.is_two_tile_ff_in_region(self,region)
   680     10391       4062.0      0.4      0.0              for ff_group in ff_groups_in_region:
   681       677        245.0      0.4      0.0                  ff_groups.append(ff_group)
   682     11186       3652.0      0.3      0.0              for loc in ff_influence_locs_in_region:
   683      1472        587.0      0.4      0.0                  ff_influence_locs.append(loc)
   684      9714      32348.0      3.3      0.1              if ffd.is_region_info_complete(self,region):
   685       473        201.0      0.4      0.0                  ic_regions.append(region)
   686      3990       2309.0      0.6      0.0          self.ic_regions = ic_regions
   687      3990       1488.0      0.4      0.0          self.ff_groups = ff_groups
   688      3990       1231.0      0.3      0.0          self.ff_influence_locs = ff_influence_locs
   689      3990       9205.0      2.3      0.0          self.groups_list = groups_list
   690      3990       1729.0      0.4      0.0          mines_left = self.minecount-self.flag_count
   691      3990       1053.0      0.3      0.0          frontier_locs = []
   692     13704       4539.0      0.3      0.0          for region in self.regions_list:
   693      9714       4696.0      0.5      0.0              frontier_locs.extend(region.locs)
   694      3990       5991.0      1.5      0.0          frontier_locs = set(frontier_locs)  
   695      3990     265280.0     66.5      1.2          nonfrontier_locs = set(ul for ul in self.unrevealed_tiles if ul not in frontier_locs)
   696      3990      11054.0      2.8      0.1          self.nonfrontier_tiles = nonfrontier_locs
   697      3990      45014.0     11.3      0.2          self.nf_rep_loc = min(nonfrontier_locs) if len(nonfrontier_locs) > 0 else None
   698      3990       1527.0      0.4      0.0          if len(groups_list) == 0 and mines_left==0:
   699                                                       safe_locs = []
   700                                                       for loc in nonfrontier_locs:
   701                                                           
   702                                                           self.mine_probs[loc] = 0
   703                                                           safe_locs.append(loc)
   704                                                       return safe_locs,[]
   705      3990     198200.0     49.7      0.9          safe_locs, mine_locs = self.search_possibilities(self.regions_list,groups_list)
   706      3990       1802.0      0.5      0.0          if len(safe_locs) > 0 and not force:
   707     13849       4346.0      0.3      0.0              for loc in safe_locs:
   708     11349       5482.0      0.5      0.0                  self.mine_probs[loc]= 0
   709      7421       2423.0      0.3      0.0              for loc in mine_locs:
   710      4921       1731.0      0.4      0.0                  self.mine_probs[loc]= 1
   711                                           
   712                                                   else:
   713      1490    3914265.0   2627.0     17.9              safe_locs, mine_locs,_,total_sols= self.calc_probs_for_board(self.regions_list,groups_list,nonfrontier_locs) 
   714      1490        594.0      0.4      0.0              self.total_sols = total_sols
   715      3990       1784.0      0.4      0.0          return safe_locs,mine_locs

